"""`count x in xs: P` y `sum x in xs: e` en los contratos (issue #5): contar y sumar con una
condición, lo que Python dice con `sum(1 for x in xs if P)` y Sello solo podía acotar."""

from __future__ import annotations

import pytest
from conftest import fails_with

from sello.compile import check_source
from sello.hash import hash_program
from sello.interp import Interpreter
from sello.nodes import Program
from sello.parser import parse, parse_expr
from sello.pretty import unparse


def ev(src: str) -> object:
    return Interpreter(Program([])).eval(parse_expr(src), {})


def test_semantica_de_count_y_sum():
    assert ev("count x in [1, 5, 7]: x > 4") == 2
    assert ev("count x in []: true") == 0
    assert ev("count i in 0..10: i % 3 == 0") == 4
    assert ev("count i in 5..2: true") == 0
    assert ev("sum x in [1, 2, 3]: x * 2") == 12
    assert ev("sum i in 1..4: i") == 6
    assert ev("sum x in []: x") == 0
    # El `count(xs, x)` de siempre sigue siendo una llamada.
    assert ev("count([1, 2, 1], 1)") == 2


def test_se_compara_con_parentesis_o_al_final_y_se_reimprime_igual():
    for src in ("result == (count x in xs: x > t)", "result == count x in xs: x > t",
                "(sum i in 0..len(xs): xs[i]) >= 0"):
        e = parse_expr(src)
        assert unparse(parse_expr(unparse(e))) == unparse(e)
    assert unparse(parse_expr("result == count x in xs: x > t")) == "(result == (count x in xs: (x > t)))"


def _fn(ensures: str, body: str = "0", params: str = "xs: List[Int], t: Int", ex: str = "f([], 0) == 0") -> str:
    return (f"fn f({params}) -> Int\n  requires 1 == 1\n  ensures {ensures}\n  effects pure\n"
            f"  example {ex}\n{{ {body} }}\n")


def test_tipos_y_solo_en_contratos():
    assert fails_with(_fn("result == (count x in xs: x + 1)"), "E400")
    assert fails_with(_fn("result == (sum x in xs: x > 1)"), "E400")
    assert fails_with(_fn("result >= 0", body="count x in xs: x > t"), "E401")


def test_count_y_sum_no_tienen_el_mismo_hash():
    a = hash_program(parse(_fn("result == (count x in xs: x > t)")))["f"]
    b = hash_program(parse(_fn("result == (sum x in xs: x > t)".replace("x > t", "x"))))["f"]
    assert a != b


COUNT_GREATER = """
fn count_greater(xs: List[Int], t: Int) -> Int
  requires 1 == 1
  ensures result == (count x in xs: x > t)
  effects pure
  example count_greater([1, 5, 7], 4) == 2
  example count_greater([], 4) == 0
{
  match xs {
    [] => 0
    [h, ..r] => (if h > t then 1 else 0) + count_greater(r, t)
  }
}
"""


def test_count_sobre_la_lista_se_prueba():
    r = check_source(COUNT_GREATER)
    assert r["functions"][0]["level"] >= 2, r


def test_count_rechaza_un_cuerpo_que_cuenta_de_mas():
    e = fails_with(COUNT_GREATER.replace("if h > t", "if h >= t"), "E201")
    assert e.extra["found_by"] == "prover"


TOTAL = """
fn total(xs: List[Int]) -> Int
  requires 1 == 1
  ensures result == (sum x in xs: x)
  effects pure
  example total([1, 2, 3]) == 6
{
  match xs {
    [] => 0
    [h, ..r] => h + total(r)
  }
}
"""


def test_sum_sobre_la_lista_se_prueba():
    r = check_source(TOTAL)
    assert r["functions"][0]["level"] >= 2, r


DOWN = """
fn upto(n: Int, k: Int) -> Int
  requires n >= 1 and k >= 0
  ensures result == (count d in 1..k + 1: d * 2 <= n)
  effects pure
  example upto(6, 6) == 3
{
  if k == 0 then 0 else (if k * 2 <= n then 1 else 0) + upto(n, k - 1)
}
"""

UP = """
fn from(i: Int, n: Int) -> Int
  requires i >= 0 and i <= n
  ensures result == (sum j in i..n: j)
  effects pure
  example from(0, 4) == 6
{
  if i == n then 0 else i + from(i + 1, n)
}
"""


@pytest.mark.parametrize("src", [DOWN, UP], ids=["hacia-abajo", "hacia-arriba"])
def test_count_y_sum_sobre_un_rango_se_prueban_en_los_dos_sentidos(src):
    r = check_source(src)
    assert r["functions"][0]["level"] >= 2, r


def test_dentro_de_otro_cuantificador_no_confunde_la_variable():
    """La `i` de fuera es un parámetro de la función de Z3, no una constante global: si se
    confundiera, Z3 «probaría» un contrato falso."""
    src = """
fn f(xs: List[Int]) -> Int
  requires distinct(xs)
  ensures forall i in 0..len(xs): (count j in 0..len(xs): xs[j] > xs[i]) < 1
  effects pure
  example f([]) == 0
{ 0 }
"""
    from sello.errors import SelloError
    try:
        r = check_source(src)
    except SelloError as e:
        assert e.code == "E201"
    else:
        assert r["functions"][0]["level"] < 2, r
