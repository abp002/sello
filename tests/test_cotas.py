"""Recuento 'ensures solo de cotas': la regla prerregistrada no miente.

Como test_mutantes: si `es_cota` llamara cota a un `contains` o contenido a
`result >= 0 and result < len(xs)`, el recuento mediría otra cosa.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench"))
import cotas  # noqa: E402

from sello.parser import parse, parse_expr  # noqa: E402


@pytest.mark.parametrize("clausula", [
    "result >= 1",
    "result >= 0 and result < len(xs)",
    "result == lo or result == x or result == hi",
    "len(result) == len(xs) - k",
    "not result > n * 2",
    "result == true or result == false",
])
def test_cota(clausula):
    assert cotas.es_cota(parse_expr(clausula))


@pytest.mark.parametrize("clausula", [
    "contains(xs, result)",
    "forall x in xs: x <= result",
    "exists v in xs: result == Some(v)",
    "count(xs, result) > 0",
    "sorted(result)",
    "is_sorted_desc(result)",
    "result >= 1 and contains(xs, result)",
    "get_at(xs, result) == Some(x)",
    "len(sin_ceros(result)) == 0",
])
def test_contenido(clausula):
    assert not cotas.es_cota(parse_expr(clausula))


SRC = """
fn f(xs: List[Int]) -> Int
  requires len(xs) > 0
  ensures result >= 1
  ensures result <= len(xs)
  effects pure
  example f([1]) == 1
{ 1 }

fn g(xs: List[Int]) -> Int
  requires len(xs) > 0
  ensures result >= 1
  ensures has_run(xs, result)
  effects pure
  example g([1]) == 1
{ 1 }

fn has_run(xs: List[Int], k: Int) -> Bool
  requires k >= 0
  ensures result == true or result == false
  effects pure
  example has_run([1], 1) == true
{ true }
"""


def test_solo_cotas_por_funcion():
    fns = {fn.name: fn for fn in parse(SRC).fns}
    assert cotas.solo_cotas(fns["f"])
    assert not cotas.solo_cotas(fns["g"])
    assert cotas.llamadas(fns["g"].ensures[1]) == {"has_run"}


def test_cambio_tras_e201():
    a = SRC
    b = SRC.replace("ensures has_run(xs, result)", "ensures result >= 0")
    fb = '{"code": "E201", "where": {"function": "g"}}'
    row = {"detail": [
        {"n": 1, "sello_error": "E201", "feedback": fb, "code": a},
        {"n": 2, "sello_error": None, "feedback": "", "code": b},
    ]}
    (c,) = cotas.cambios_tras_e201(row)
    assert c["fn"] == "g" and c["cambiado"]
    assert c["antes"] == ["(result >= 1)", "has_run(xs, result)"]
    assert c["despues"] == ["(result >= 1)", "(result >= 0)"]
