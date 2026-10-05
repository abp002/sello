"""El almacén: verificada una vez, verificada para siempre; las versiones coexisten."""

import pytest

from sello.errors import SelloError
from sello.hash import short
from sello.store import Store

LIB = """
fn head(xs: List[Int]) -> Option[Int]
  requires 1 == 1
  ensures 1 == 1
  effects pure
  example head([]) == None
  example head([1, 2]) == Some(1)
{ match xs { [] => None  [h, ..t] => Some(h) } }

fn first_or(xs: List[Int], d: Int) -> Int
  requires 1 == 1
  ensures 1 == 1
  effects pure
  example first_or([], 9) == 9
  example first_or([4, 5], 9) == 4
{ match head(xs) { None => d  Some(x) => x } }
"""


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "store.db")


def test_add_verifica_y_la_segunda_vez_cachea(store):
    first = store.add(LIB)
    assert [f["cached"] for f in first] == [False, False]
    assert all(f["certificate"]["ok"] for f in first)
    assert [f["cached"] for f in store.add(LIB)] == [True, True]


def test_cambiar_el_llamador_no_reverifica_al_llamado(store):
    store.add(LIB)
    out = store.add(LIB.replace("None => d", "None => d + 1").replace("first_or([], 9) == 9", "first_or([], 9) == 10"))
    by = {f["name"]: f for f in out}
    assert by["head"]["cached"] is True
    assert by["first_or"]["cached"] is False


def test_ejemplo_que_falla_deja_certificado_fallido_y_no_crea_alias(store):
    roto = LIB.replace("first_or([], 9) == 9", "first_or([], 9) == 0")
    with pytest.raises(SelloError) as ei:
        store.add(roto)
    assert ei.value.code == "E200"
    assert [n["name"] for n in store.names()] == ["head"]
    with pytest.raises(SelloError):
        store.add(roto)


def test_renombrar_apunta_dos_nombres_al_mismo_hash(store):
    store.add(LIB)
    store.add(LIB.replace("fn head", "fn primero").replace("head(xs)", "primero(xs)").replace("head([", "primero(["))
    names = {n["name"]: n["hash"] for n in store.names()}
    assert names["head"] == names["primero"]


def test_sig_no_lleva_cuerpo_y_deps_users_cruzan(store):
    store.add(LIB)
    s = store.sig("first_or")
    assert "source" not in s and s["signature"] == "first_or(xs: List[Int], d: Int) -> Int"
    assert s["certificate"]["ok"] and s["certificate"]["examples"] == 2
    assert [d["name"] for d in store.deps("first_or")] == ["head"]
    assert [u["name"] for u in store.users("head")] == ["first_or"]


def test_la_version_vieja_sigue_usando_su_dependencia_vieja(store):
    store.add(LIB)
    old_first_or = store.resolve("first_or")
    old_head = store.resolve("head")
    # head cambia de significado: first_or se reverifica contra el nuevo head
    store.add(LIB.replace("[h, ..t] => Some(h)", "[h, ..t] => Some(h + 100)")
                 .replace("head([1, 2]) == Some(1)", "head([1, 2]) == Some(101)")
                 .replace("first_or([4, 5], 9) == 4", "first_or([4, 5], 9) == 104"))
    assert store.resolve("head") != old_head and store.resolve("first_or") != old_first_or
    program, _ = store.load_closure([old_first_or])
    assert {f.name for f in program.fns} == {f"f_{short(old_first_or)}", f"f_{short(old_head)}"}
    assert store.eval("first_or([4, 5], 9)") == "104"


def test_verify_detecta_un_certificado_que_miente(store):
    store.add(LIB)
    h = store.resolve("first_or")
    store.db.execute("UPDATE certificates SET ok = 0 WHERE hash = ?", (h,)); store.db.commit()
    assert store.verify("first_or")["certificate"]["ok"] is True


# Regresión (2026-09-05): el reimpresor perdía los paréntesis de un `forall` operando, así que
# el texto guardado era otro programa que el hasheado. `f([])` violaba el ensures en directo
# (E201) pero, cargada desde el almacén, devolvía 1 con certificado ok.
FORALL_OPERANDO = """
fn f(xs: List[Int]) -> Int
  requires len(xs) >= 0
  ensures (forall x in xs: x > 0) and result == 0
  effects pure
  example f([1]) == 0
{ if xs == [] then 1 else 0 }
"""


def test_el_texto_guardado_es_el_mismo_programa_que_el_hash(store):
    from sello.hash import hash_program
    from sello.interp import Interpreter
    from sello.parser import parse
    # Desde el 2026-09-06 el probador encuentra f([]) al añadir; la función se guarda sin alias
    with pytest.raises(SelloError) as ei:
        store.add(FORALL_OPERANDO)
    assert ei.value.code == "E201" and ei.value.extra["input"] == "f([])"
    h = hash_program(parse(FORALL_OPERANDO))["f"]
    guardado = parse(store.function(h)["source"])
    assert hash_program(guardado)["f"] == h
    with pytest.raises(SelloError) as ei:  # el texto guardado conserva los paréntesis: f([]) sigue violando el ensures
        Interpreter(guardado).call("f", [[]])
    assert ei.value.code == "E201"
    assert store.names() == []


def test_add_se_niega_si_el_texto_canonico_no_reproduce_la_funcion(store, monkeypatch):
    """La guarda del almacén: si el reimpresor volviera a ser infiel, E501 y nada guardado."""
    import sello.store as st
    fiel = st.unparse_fn
    monkeypatch.setattr(st, "unparse_fn", lambda fn: fiel(fn).replace("Some(h)", "None"))
    with pytest.raises(SelloError) as ei:
        store.add(LIB)
    assert ei.value.code == "E501"
    assert store.names() == []


# ---- nivel 2 (2026-09-06) ----

FACT = """
fn factorial(n: Int) -> Int
  requires n >= 0
  ensures result >= 1
  effects pure
  example factorial(0) == 1
{ if n == 0 then 1 else n * factorial(n - 1) }
"""

CLAMP_MAL = """
fn clamp(x: Int, lo: Int, hi: Int) -> Int
  requires lo <= hi
  ensures x >= lo or result == lo
  effects pure
  example clamp(5, 1, 10) == 5
{ if x < lo then hi else x }
"""


def test_lo_que_el_probador_prueba_lleva_certificado_de_nivel_2(store):
    [f] = store.add(FACT)
    assert f["certificate"]["level"] == 2 and f["certificate"]["ok"]
    assert store.sig("factorial")["certificate"]["level"] == 2
    assert store.verify("factorial")["certificate"]["level"] == 2
    assert store.sig("factorial")["certificate"]["closure_level"] == 2  # se llama a sí misma


def test_lo_que_no_prueba_se_queda_en_nivel_1(store):
    src = FACT.replace("ensures result >= 1", "ensures result >= 1 and result >= n")  # n*r >= n con r >= 1: no lineal
    [f] = store.add(src)
    assert f["certificate"]["ok"] and f["certificate"]["level"] in (1, 2)
    roto = """
fn f(n: Int) -> Int
  requires n >= 0
  ensures result == 42
  effects pure
  example f(0) == 42
{ if n == 0 then 42 else f(n) }
"""
    [g] = store.add(roto)  # sin medida de terminación: nivel 1, pero certificada por ejemplos
    assert g["certificate"] == {**g["certificate"], "level": 1, "ok": True}


def test_un_contraejemplo_del_probador_deja_certificado_fallido_y_no_crea_alias(store):
    with pytest.raises(SelloError) as ei:
        store.add(CLAMP_MAL)
    assert ei.value.code == "E201" and ei.value.extra["found_by"] == "prover"
    assert store.names() == []
    from sello.hash import hash_program
    from sello.parser import parse
    cert = store.certificate(hash_program(parse(CLAMP_MAL))["clamp"])
    assert cert["ok"] is False and cert["error"]["found_by"] == "prover"


# ---------- enlace: llamar a lo guardado sin copiarlo al fuente (ALE-170) ----------

INC = """
fn inc(x: Int) -> Int
  requires x >= 0
  ensures result == x + 1
  effects pure
  example inc(1) == 2
{ x + 1 }
"""

INC2 = """
fn inc2(x: Int) -> Int
  requires x >= 0
  ensures result == x + 2
  effects pure
  example inc2(3) == 5
{ inc(inc(x)) }
"""


def test_add_enlaza_una_funcion_del_almacen_con_el_mismo_hash_que_en_el_fuente(tmp_path):
    junto = Store(tmp_path / "junto.db").add(INC + INC2)
    separado = Store(tmp_path / "separado.db")
    separado.add(INC)
    out = separado.add(INC2)
    assert [f["name"] for f in out] == ["inc2"]
    assert out[0]["hash"] == {f["name"]: f for f in junto}["inc2"]["hash"]
    assert separado.deps("inc2") == [{"name": "inc", "hash": separado.sig("inc")["hash"]}]
    assert "inc(inc(x))" in separado.view("inc2")["source"]


def test_add_enlazado_prueba_con_el_contrato_de_lo_guardado(store):
    store.add(INC)
    assert store.add(INC2)[0]["certificate"]["level"] == 2


def test_add_enlazado_caza_un_contrato_que_lo_guardado_contradice(store):
    store.add(INC)
    with pytest.raises(SelloError) as ei:
        store.add(INC2.replace("x + 2", "x + 3").replace("inc2(3) == 5", "inc2(3) >= 0"))
    assert ei.value.code == "E201"


# Regresión de flujo-2026-10-01-1914-control, second_largest: el find_in_list de haiku viola su
# contrato (find_in_list([-1], [14]) da Some(-1)). En un fichero con los helpers del contrato, E201;
# con ellos enlazados desde el almacén, nivel 1. El primer modelo de Z3 no se reproducía y no se
# pedía otro: lo decidían los nombres (f_<hash> frente a is_second). Fuentes tal cual, porque de
# ellas salen los hashes y de los hashes, el modelo.
SL_HELPERS = """
fn has(xs: List[Int], v: Int) -> Bool
  requires (len(xs) >= 0)
  ensures (result == contains(xs, v))
  effects pure
  example (has([3, 9, 1], 9) == true)
  example (has([3, 9, 1], 4) == false)
  example (has([], 1) == false)
{
  match xs { [] => false [h, ..t] => ((h == v) or has(t, v)) }
}

fn greater_count(xs: List[Int], v: Int) -> Int
  requires (len(xs) >= 0)
  ensures ((result >= 0) and (result <= len(xs)))
  ensures ((result == 0) or (exists x in xs: (x > v)))
  ensures ((result > 0) or (forall x in xs: (x <= v)))
  effects pure
  example (greater_count([3, 9, 1], 3) == 1)
  example (greater_count([3, 9, 1], 9) == 0)
  example (greater_count([3, 9, 1], 1) == 2)
  example (greater_count([], 5) == 0)
{
  match xs { [] => 0 [h, ..t] => if (h > v) then (1 + greater_count(t, v)) else greater_count(t, v) }
}

fn is_second(xs: List[Int], r: Option[Int]) -> Bool
  requires (len(xs) >= 0)
  ensures ((r != None) or (result == (len(xs) < 2)))
  effects pure
  example (is_second([3, 9, 1], Some(3)) == true)
  example (is_second([3, 9, 1], Some(9)) == false)
  example (is_second([3, 9, 1], Some(1)) == false)
  example (is_second([3, 9, 1], Some(7)) == false)
  example (is_second([3, 9, 1], None) == false)
  example (is_second([4], None) == true)
  example (is_second([4], Some(4)) == false)
  example (is_second([], None) == true)
{
  match r { None => match xs { [] => true [_, ..t] => match t { [] => true _ => false } } Some(v) => (has(xs, v) and (greater_count(xs, v) == 1)) }
}
"""

SL_CUERPO = """
fn find_in_list(current: List[Int], original: List[Int]) -> Option[Int]
  requires distinct(original)
  ensures is_second(original, result)
  effects pure
  example (find_in_list([3, 9, 1], [3, 9, 1]) == Some(3))
  example (find_in_list([4], [4]) == None)
  example (find_in_list([], []) == None)
  example (find_in_list([5, 2], [5, 2]) == Some(2))
  example (find_in_list([1, 2, 3, 4], [1, 2, 3, 4]) == Some(3))
{
  match current { [] => None [x, ..t] => if (greater_count(original, x) == 1) then Some(x) else find_in_list(t, original) }
}

fn second_largest(xs: List[Int]) -> Option[Int]
  requires distinct(xs)
  ensures is_second(xs, result)
  effects pure
  example (second_largest([3, 9, 1]) == Some(3))
  example (second_largest([4]) == None)
  example (second_largest([]) == None)
  example (second_largest([5, 2]) == Some(2))
  example (second_largest([1, 2, 3, 4]) == Some(3))
{
  find_in_list(xs, xs)
}
"""


@pytest.mark.parametrize("enlazado", [False, True], ids=["en-el-fichero", "enlazado"])
def test_un_helper_que_viola_su_contrato_se_caza_igual_enlazado_que_en_el_fichero(store, enlazado):
    if enlazado:
        store.add(SL_HELPERS)
    with pytest.raises(SelloError) as ei:
        store.add(SL_CUERPO if enlazado else SL_HELPERS + SL_CUERPO)
    assert ei.value.code == "E201" and ei.value.function == "find_in_list"
    assert ei.value.extra["found_by"] == "prover"
    assert not {"find_in_list", "second_largest"} & {n["name"] for n in store.names()}


def test_check_con_almacen_enlaza_y_solo_informa_del_fuente(store):
    from sello.compile import check_source
    store.add(INC)
    out = check_source(INC2, store=store)
    assert [f["name"] for f in out["functions"]] == ["inc2"]
    assert out["functions"][0]["level"] == 2


def test_nombre_que_no_esta_ni_en_el_fuente_ni_en_el_almacen_es_E401(store):
    store.add(INC)
    with pytest.raises(SelloError) as ei:
        store.add(INC2.replace("inc(inc(x))", "dec(inc(x))"))
    assert ei.value.code == "E401"


def test_add_sube_un_certificado_de_nivel_1_si_ahora_se_prueba(store):
    """ALE-171: un nivel 1 en caché no es definitivo; el add vuelve a intentar el probador."""
    store.add(INC)
    store.db.execute("UPDATE certificates SET level = 1")
    store.db.commit()
    out = store.add(INC)
    assert out[0]["cached"] is False
    assert out[0]["certificate"]["level"] == 2


# ---------- lo que un nivel 2 da por bueno (2026-09-29) ----------

# f no termina para n >= 1 (ninguna medida decrece): se queda en nivel 1 para siempre, con sus
# ejemplos pasados. g se prueba en nivel 2 con el contrato de f, que nadie ha probado, y g(1)
# tampoco termina.
NO_TERMINA = """
fn f(n: Int) -> Int
  requires n >= 0
  ensures result == 42
  effects pure
  example f(0) == 42
{ if n == 0 then 42 else f(n) }
"""

LLAMA_A_F = """
fn g(n: Int) -> Int
  requires n >= 0
  ensures result == 43
  effects pure
  example g(0) == 43
{ f(n) + 1 }
"""


def test_si_el_llamado_falla_no_se_guarda_quien_lo_llama_aunque_vaya_antes(store):
    """Regresión: add certificaba en el orden del fichero y se paraba en el primer fallo, así que
    un llamador que iba delante se quedaba con alias y nivel 2 sobre un llamado roto."""
    with pytest.raises(SelloError) as ei:
        store.add(LLAMA_A_F + NO_TERMINA.replace("f(0) == 42", "f(0) == 41"))
    assert ei.value.code == "E200"
    assert store.names() == []


# impar va antes que par en el fichero y en el orden de la componente: si par falla, impar ya
# se ha certificado.
PARIDAD = """
fn impar(n: Int) -> Bool
  requires n >= 0
  ensures 1 == 1
  effects pure
  example impar(3) == true
{ if n == 0 then false else par(n - 1) }

fn par(n: Int) -> Bool
  requires n >= 0
  ensures 1 == 1
  effects pure
  example par(4) == true
{ if n == 0 then true else impar(n - 1) }
"""


def test_un_ciclo_se_guarda_entero_o_no_se_guarda(store):
    """Regresión: dentro de un ciclo no hay orden de dependencias que valga. impar llama a par,
    así que no puede quedarse con alias si par falla después."""
    with pytest.raises(SelloError):
        store.add(PARIDAD.replace("par(4) == true", "par(4) == false"))
    assert store.names() == []
    assert [f["name"] for f in store.add(PARIDAD)] == ["impar", "par"]


def test_un_nivel_2_dice_en_que_nivel_1_se_apoya(store):
    g = {f["name"]: f for f in store.add(LLAMA_A_F + NO_TERMINA)}["g"]  # g delante de f
    f = {"name": "f", "hash": store.sig("f")["hash"], "level": 1}
    for cert in (g["certificate"], store.sig("g")["certificate"], store.verify("g")["certificate"]):
        assert cert["level"] == 2  # modular: con el contrato de f
        assert cert["closure_level"] == 1 and cert["rests_on"] == [f]
    assert store.sig("f")["certificate"]["rests_on"] == []  # su propio nivel ya lo dice


def test_el_cierre_llega_a_lo_que_se_llama_de_segunda_mano(store):
    store.add(NO_TERMINA + LLAMA_A_F)
    [h] = store.add("""
fn h(n: Int) -> Int
  requires n >= 0
  ensures result == 44
  effects pure
  example h(0) == 44
{ g(n) + 1 }
""")
    assert h["certificate"]["level"] == 2 and h["certificate"]["closure_level"] == 1
    assert [d["name"] for d in h["certificate"]["rests_on"]] == ["f"]  # g es nivel 2: no se lista


def test_una_dependencia_fallida_baja_el_cierre_a_0(store):
    store.add(NO_TERMINA + LLAMA_A_F)
    f = store.resolve("f")  # como si un verify posterior la hubiera tumbado
    store.db.execute("UPDATE certificates SET ok = 0 WHERE hash = ?", (f,)); store.db.commit()
    cert = store.sig("g")["certificate"]
    assert cert["closure_level"] == 0 and cert["rests_on"] == [{"name": "f", "hash": short(f), "level": 0}]
