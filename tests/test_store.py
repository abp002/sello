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
