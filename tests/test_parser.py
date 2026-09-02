from conftest import MAX

from sello.nodes import INT, Binary, If, Match, PCons, PEmpty, TList, TOption
from sello.parser import parse, parse_expr
from sello.pretty import unparse


def test_parsea_funcion_con_contrato():
    fn = parse(MAX).fns[0]
    assert fn.name == "max"
    assert [p.name for p in fn.params] == ["a", "b"]
    assert len(fn.requires) == 1 and len(fn.ensures) == 1
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


def test_comodin_dentro_del_patron_de_lista():
    """Hallazgo de la batería difícil (2026-09-02): haiku escribe `[_, ..t]` y `[h, .._]`."""
    src = """
fn tail_len(xs: List[Int]) -> Int
  requires true
  ensures result >= 0
  effects pure
  example tail_len([]) == 0
  example tail_len([1, 2, 3]) == 2
{ match xs { [] => 0  [_, ..t] => length_of(t) } }

fn length_of(xs: List[Int]) -> Int
  requires true
  ensures result >= 0
  effects pure
  example length_of([1, 2]) == 2
{ match xs { [] => 0  [h, .._] => 1 + length_of(rest(xs)) } }

fn rest(xs: List[Int]) -> List[Int]
  requires xs != []
  ensures true
  effects pure
  example rest([1, 2]) == [2]
{ match xs { [] => []  [_, ..t] => t } }
"""
    from sello.compile import check_source
    assert check_source(src)["ok"]
