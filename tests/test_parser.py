from conftest import MAX

from sello.nodes import INT, Binary, If, Match, PCons, PEmpty, TList, TOption
from sello.parser import parse, parse_expr
from sello.pretty import unparse


def test_parsea_funcion_con_contrato():
    fn = parse(MAX).fns[0]
    assert fn.name == "max"
    assert [p.name for p in fn.params] == ["a", "b"]
    assert fn.requires is not None and fn.ensures is not None
    assert fn.effects == "pure" and len(fn.examples) == 1
    assert isinstance(fn.body, If)


def test_precedencia_aritmetica_y_logica():
    e = parse_expr("1 + 2 * 3 == 7 and not false")
    assert isinstance(e, Binary) and e.op == "and"
    assert unparse(e.left) == "((1 + (2 * 3)) == 7)"


def test_tipos_anidados_y_match():
    src = """
fn f(xs: List[Option[Int]]) -> Int
  requires true
  ensures true
  effects pure
  example f([]) == 0
{ match xs { [] => 0  [h, ..t] => 1 + f(t) } }
"""
    fn = parse(src).fns[0]
    assert fn.params[0].type == TList(TOption(INT))
    assert isinstance(fn.body, Match)
    assert isinstance(fn.body.arms[0].pattern, PEmpty)
    assert isinstance(fn.body.arms[1].pattern, PCons)


def test_error_de_sintaxis_lleva_posicion():
    from sello.errors import SelloError
    import pytest
    with pytest.raises(SelloError) as ei:
        parse("fn f(a: Int) -> Int\n  requires true\n{ a + }")
    assert ei.value.code == "E000"
    assert ei.value.line == 3
