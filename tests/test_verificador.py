"""El certificado dice con qué verificador se dio, y uno de otro verificador no vale como caché (SEL-7)."""

import sqlite3

import pytest

import sello.store
from sello.store import Store
from sello.verifier import code_hash, fingerprint

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


def otro_verificador(monkeypatch, **cambios):
    monkeypatch.setattr(sello.store, "fingerprint", lambda: {**fingerprint(), **cambios})


def by_name(out):
    return {f["name"]: f for f in out}


def test_el_certificado_guarda_la_huella_del_verificador(store):
    cert = by_name(store.add(LIB))["head"]["certificate"]
    assert cert["verifier"] == fingerprint()
    assert "stale" not in cert


def test_con_otro_codigo_de_sello_el_nivel_2_no_se_reutiliza(store, monkeypatch):
    store.add(LIB)
    otro_verificador(monkeypatch, sello="otro")
    out = store.add(LIB)
    assert [f["cached"] for f in out] == [False, False]
    assert by_name(out)["head"]["certificate"]["verifier"]["sello"] == "otro"


def test_con_otra_version_de_z3_el_nivel_2_no_se_reutiliza(store, monkeypatch):
    store.add(LIB)
    otro_verificador(monkeypatch, z3="0.0.0")
    assert [f["cached"] for f in store.add(LIB)] == [False, False]


def test_otra_maquina_no_invalida_pero_queda_apuntada(store, monkeypatch):
    store.add(LIB)
    otro_verificador(monkeypatch, arch="x86_64" if fingerprint()["arch"] != "x86_64" else "arm64")
    out = store.add(LIB)
    assert [f["cached"] for f in out] == [True, True]
    assert by_name(out)["head"]["certificate"]["verifier"]["arch"] == fingerprint()["arch"]


def test_un_certificado_viejo_se_lee_como_viejo_y_no_sostiene_el_cierre(store, monkeypatch):
    store.add(LIB)
    otro_verificador(monkeypatch, sello="otro")
    cert = store.sig("first_or")["certificate"]
    assert cert["stale"] is True
    assert cert["closure_level"] == 0
    assert {"name": "head", "level": 0, "stale": True}.items() <= cert["rests_on"][0].items()


def test_reverify_pone_al_dia_lo_viejo(store, monkeypatch):
    store.add(LIB)
    otro_verificador(monkeypatch, sello="otro")
    hechos = store.reverify()
    assert sorted(r["name"] for r in hechos) == ["first_or", "head"]
    cert = store.sig("first_or")["certificate"]
    assert "stale" not in cert and cert["closure_level"] == 2
    assert store.reverify() == []


def test_un_almacen_sin_huellas_tiene_todo_viejo(tmp_path):
    store = Store(tmp_path / "store.db")
    store.add(LIB)
    store.db.close()
    db = sqlite3.connect(tmp_path / "store.db")
    db.execute("UPDATE certificates SET verifier = NULL")
    db.commit()
    db.close()
    store = Store(tmp_path / "store.db")
    assert store.sig("head")["certificate"]["stale"] is True
    assert [f["cached"] for f in store.add(LIB)] == [False, False]


# ---------- la huella del código ----------

CODIGO = '''
"""Docstring del módulo."""
LIMITE = 10  # un comentario

def f(x):
    """Lo que hace f."""
    return x + LIMITE
'''


def test_la_huella_del_codigo_ignora_comentarios_y_docstrings():
    otro = CODIGO.replace("un comentario", "otro").replace("Lo que hace f.", "Otra cosa.").replace(
        "Docstring del módulo.", "Cambiado.")
    assert code_hash([CODIGO]) == code_hash([otro])


def test_la_huella_del_codigo_cambia_con_el_codigo():
    assert code_hash([CODIGO]) != code_hash([CODIGO.replace("LIMITE = 10", "LIMITE = 11")])


def test_una_funcion_que_solo_tiene_docstring_sigue_siendo_codigo():
    solo_doc = 'def g():\n    """Nada."""\n'
    assert code_hash([solo_doc]) != code_hash(["def g():\n    return 1\n"])
