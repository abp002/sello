"""Los contratos son la regla de negocio de Sello: se testean en detalle."""

from conftest import fails_with

from sello.compile import check_source

FACT = """
fn factorial(n: Int) -> Int
  requires n >= 0
  ensures result >= 1
  effects pure
  example factorial(0) == 1
  example factorial(5) == 120
{ if n == 0 then 1 else n * factorial(n - 1) }
"""


def test_ejemplo_que_falla_es_E200_con_esperado_y_obtenido():
    src = FACT.replace("factorial(5) == 120", "factorial(5) == 121")
    e = fails_with(src, "E200")
    assert e.extra == {"expected": "121", "got": "120"}
    assert e.function == "factorial"


def test_precondicion_violada_desde_ejemplo_es_E300():
    src = FACT.replace("example factorial(0) == 1", "example factorial(-1) == 1")
    e = fails_with(src, "E300")
    assert e.extra["call"] == "factorial(-1)"


def test_precondicion_violada_desde_otra_funcion_señala_al_llamador():
    src = FACT + """
fn bad(n: Int) -> Int
  requires true
  ensures true
  effects pure
  example bad(3) == 2
{ factorial(n - 5) }
"""
    e = fails_with(src, "E300")
    assert e.function == "bad"


def test_postcondicion_violada_es_E201():
    src = FACT.replace("ensures result >= 1", "ensures result > 200")
    e = fails_with(src, "E201")
    assert e.extra["got"] == "1"


def test_todo_correcto_devuelve_resumen_con_firmas():
    r = check_source(FACT)
    assert r == {"ok": True, "examples": 2,
                 "functions": [{"name": "factorial", "signature": "factorial(n: Int) -> Int", "examples": 2}]}


CLAMP_DOBLE = """
fn clamp(x: Int, lo: Int, hi: Int) -> Int
  requires lo <= hi
  ensures result >= lo
  ensures result <= hi
  effects pure
  example clamp(5, 1, 10) == 5
  example clamp(-5, 1, 10) == 1
{ if x < lo then lo else if x > hi then hi else x }
"""


def test_varias_clausulas_ensures_son_conjuncion():
    """Hallazgo de la medición 2026-09-02: el modelo escribe dos `ensures` como en Dafny."""
    assert check_source(CLAMP_DOBLE)["ok"]
    roto = CLAMP_DOBLE.replace("ensures result <= hi", "ensures result <= 4")
    e = fails_with(roto, "E201")
    assert "result <= 4" in e.detail
