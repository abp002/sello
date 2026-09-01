"""El hash es la identidad: lo que no cambia el significado no cambia el hash."""

import re

from sello.hash import hash_program
from sello.parser import parse

FACT = """
fn factorial(n: Int) -> Int
  requires n >= 0
  ensures result >= 1
  effects pure
  example factorial(5) == 120
{ if n == 0 then 1 else n * factorial(n - 1) }
"""

EVEN_ODD = """
fn is_even(n: Int) -> Bool
  requires n >= 0
  ensures true
  effects pure
  example is_even(4) == true
{ if n == 0 then true else is_odd(n - 1) }

fn is_odd(n: Int) -> Bool
  requires n >= 0
  ensures true
  effects pure
  example is_odd(3) == true
{ if n == 0 then false else is_even(n - 1) }
"""


def h(src: str) -> dict[str, str]:
    return hash_program(parse(src))


def test_renombrar_parametro_no_cambia_el_hash():
    assert h(FACT)["factorial"] == h(re.sub(r"\bn\b", "k", FACT))["factorial"]


def test_renombrar_la_funcion_no_cambia_el_hash():
    assert h(FACT)["factorial"] == h(FACT.replace("factorial", "fact"))["fact"]


def test_cambiar_el_cuerpo_o_el_contrato_cambia_el_hash():
    base = h(FACT)["factorial"]
    assert h(FACT.replace("n * factorial", "n + factorial"))["factorial"] != base
    assert h(FACT.replace("ensures result >= 1", "ensures result >= 0"))["factorial"] != base
    assert h(FACT.replace("example factorial(5) == 120", "example factorial(3) == 6"))["factorial"] != base


def test_cambiar_una_dependencia_cambia_al_llamador():
    src = FACT + "\nfn twice(n: Int) -> Int\n  requires n >= 0\n  ensures true\n  effects pure\n  example twice(3) == 12\n{ 2 * factorial(n) }\n"
    a = h(src)
    b = h(src.replace("ensures result >= 1", "ensures result >= 0"))
    assert a["twice"] != b["twice"]


def test_recursion_mutua_es_estable_y_sensible():
    a = h(EVEN_ODD)
    renamed = h(EVEN_ODD.replace("is_even", "par").replace("is_odd", "impar"))
    assert a["is_even"] == renamed["par"] and a["is_odd"] == renamed["impar"]
    assert a["is_even"] != a["is_odd"]
    changed = h(EVEN_ODD.replace("if n == 0 then false", "if n == 1 then true"))
    assert changed["is_even"] != a["is_even"] and changed["is_odd"] != a["is_odd"]
