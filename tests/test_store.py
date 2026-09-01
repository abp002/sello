"""El almacén: verificada una vez, verificada para siempre; las versiones coexisten."""

import pytest

from sello.errors import SelloError
from sello.hash import short
from sello.store import Store

LIB = """
fn head(xs: List[Int]) -> Option[Int]
  requires true
  ensures true
  effects pure
  example head([]) == None
  example head([1, 2]) == Some(1)
{ match xs { [] => None  [h, ..t] => Some(h) } }

fn first_or(xs: List[Int], d: Int) -> Int
  requires true
  ensures true
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
