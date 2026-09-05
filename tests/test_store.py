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
    from sello.parser import parse
    [added] = store.add(FORALL_OPERANDO)
    guardado = parse(store.view("f")["source"])
    assert short(hash_program(guardado)["f"]) == added["hash"]
    with pytest.raises(SelloError) as ei:
        store.eval("f([])")
    assert ei.value.code == "E201"


def test_add_se_niega_si_el_texto_canonico_no_reproduce_la_funcion(store, monkeypatch):
    """La guarda del almacén: si el reimpresor volviera a ser infiel, E501 y nada guardado."""
    import sello.store as st
    fiel = st.unparse_fn
    monkeypatch.setattr(st, "unparse_fn", lambda fn: fiel(fn).replace("Some(h)", "None"))
    with pytest.raises(SelloError) as ei:
        store.add(LIB)
    assert ei.value.code == "E501"
    assert store.names() == []
