"""Nivel 3: probada y con un contrato que fija la respuesta (SEL-13).

Nivel 2 dice que el cuerpo cumple el contrato; nivel 3, además, que el contrato no deja elegir:
cualquier otro cuerpo que lo cumpla devuelve lo mismo. Un contrato que admite dos respuestas se
queda en 2 y el certificado guarda el testigo. Decisión en el vault: 'Z3 dice si el contrato
fija una sola respuesta'.
"""

import pytest

import sello.store
from sello.compile import check_source, level
from sello.store import Store
from sello.verifier import MODULES, fingerprint

CLAMP = """
fn clamp(x: Int, lo: Int, hi: Int) -> Int
  requires lo <= hi
  ensures result >= lo and result <= hi
  ensures x < lo or x > hi or result == x
  ensures x >= lo or result == lo
  ensures x <= hi or result == hi
  effects pure
  example clamp(5, 0, 10) == 5
{ if x < lo then lo else if x > hi then hi else x }
"""

# Probada, pero el contrato acepta cualquier cota superior.
MAX = """
fn max(a: Int, b: Int) -> Int
  requires 1 == 1
  ensures result >= a and result >= b
  effects pure
  example max(1, 2) == 2
{ if a >= b then a else b }
"""

# Un llamador de nivel 3 sobre un helper de nivel 2: la unicidad de `twice` no depende de la de
# `pos`, solo de que `pos` cumpla su contrato.
CALLER = """
fn pos(x: Int) -> Int
  requires 1 == 1
  ensures result >= 0
  effects pure
  example pos(-3) == 3
{ if x < 0 then 0 - x else x }

fn twice(x: Int) -> Int
  requires 1 == 1
  ensures result == pos(x) + pos(x)
  effects pure
  example twice(-3) == 6
{ pos(x) + pos(x) }
"""


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "store.db")


def by_name(fs):
    return {f["name"]: f for f in fs}


def test_el_nivel():
    assert level(True, 0, unique=True) == 3
    assert level(True, 0, unique=False) == 2
    assert level(False, 0, unique=True) == 1  # sin prueba, la unicidad no sube nada
    assert level(True, 1, unique=True) == 3  # ejemplos pendientes de un hueco: la prueba manda, como en 2
    assert level(True, 0, hole=True, unique=True) == 0


def test_check_da_nivel_3_al_contrato_que_fija_la_respuesta():
    f = check_source(CLAMP)["functions"][0]
    assert f["level"] == 3 and f["determined"] == "unique"
    assert "witness" not in f


def test_check_deja_en_2_el_contrato_ambiguo_con_su_testigo():
    f = check_source(MAX)["functions"][0]
    assert f["level"] == 2 and f["determined"] == "ambiguous"
    w = f["witness"]
    assert w["input"].startswith("max(") and len(w["results"]) == 2 and w["results"][0] != w["results"][1]


def test_sin_probador_no_hay_unicidad():
    f = check_source(CLAMP, prover=False)["functions"][0]
    assert "determined" not in f


def test_el_almacen_guarda_el_nivel_3_y_lo_reutiliza(store):
    out = by_name(store.add(CLAMP))["clamp"]
    assert out["certificate"]["level"] == 3 and out["certificate"]["determined"] == "unique"
    assert store.sig("clamp")["certificate"]["level"] == 3
    again = by_name(store.add(CLAMP))["clamp"]
    assert again["cached"] and again["certificate"]["level"] == 3
    assert store.verify("clamp")["certificate"]["level"] == 3


def test_el_almacen_guarda_el_testigo(store):
    cert = by_name(store.add(MAX))["max"]["certificate"]
    assert cert["level"] == 2 and cert["determined"] == "ambiguous"
    assert cert["witness"]["input"].startswith("max(")


def test_el_cierre_no_baja_el_nivel_3_por_un_helper_de_nivel_2(store):
    out = by_name(store.add(CALLER))
    assert out["pos"]["certificate"]["level"] == 2
    cert = out["twice"]["certificate"]
    assert cert["level"] == 3 and cert["closure_level"] == 3 and cert["rests_on"] == []


def test_un_certificado_sin_unicidad_es_de_otro_verificador(store, monkeypatch):
    # El código que decide el nivel 3 entra en la huella: los certificados de antes de SEL-13
    # quedan viejos y `reverify` los sube.
    assert "unique" in MODULES
    monkeypatch.setattr(sello.store, "fingerprint", lambda: {**fingerprint(), "sello": "antes"})
    store.add(CLAMP)
    monkeypatch.undo()
    assert store.sig("clamp")["certificate"].get("stale")
    assert by_name(store.reverify())["clamp"]["certificate"]["level"] == 3
