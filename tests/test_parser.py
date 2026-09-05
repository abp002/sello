import pytest

from conftest import MAX

from sello.nodes import INT, Binary, If, Match, PCons, PEmpty, Quant, TList, TOption
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
  requires 1 == 1
  ensures 1 == 1
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
        parse("fn f(a: Int) -> Int\n  requires 1 == 1\n{ a + }")
    assert ei.value.code == "E000"
    assert ei.value.line == 3


def test_comodin_dentro_del_patron_de_lista():
    """Hallazgo de la batería difícil (2026-09-02): haiku escribe `[_, ..t]` y `[h, .._]`."""
    src = """
fn tail_len(xs: List[Int]) -> Int
  requires 1 == 1
  ensures result >= 0
  effects pure
  example tail_len([]) == 0
  example tail_len([1, 2, 3]) == 2
{ match xs { [] => 0  [_, ..t] => length_of(t) } }

fn length_of(xs: List[Int]) -> Int
  requires 1 == 1
  ensures result >= 0
  effects pure
  example length_of([1, 2]) == 2
{ match xs { [] => 0  [h, .._] => 1 + length_of(rest(xs)) } }

fn rest(xs: List[Int]) -> List[Int]
  requires xs != []
  ensures 1 == 1
  effects pure
  example rest([1, 2]) == [2]
{ match xs { [] => []  [_, ..t] => t } }
"""
    from sello.compile import check_source
    assert check_source(src)["ok"]


def test_cuantificador_engloba_hasta_el_final_de_la_clausula():
    e = parse_expr("forall x in xs: x == m or count(xs, x) < count(xs, m)")
    assert isinstance(e, Quant) and e.kind == "forall" and e.var == "x"
    assert isinstance(e.body, Binary) and e.body.op == "or"
    assert unparse(e) == "forall x in xs: ((x == m) or (count(xs, x) < count(xs, m)))"
    anidado = parse_expr("exists x in xs: forall y in ys: x < y")
    assert isinstance(anidado.body, Quant) and anidado.body.kind == "forall"


def test_cuantificador_como_operando_de_or():
    """Medición 2026-09-02: haiku y sonnet escribieron `a or exists ...` y era E000."""
    e = parse_expr("len(xs) == 0 or exists v in xs: result == Some(v) and v > 0")
    assert isinstance(e, Binary) and e.op == "or" and isinstance(e.right, Quant)
    assert isinstance(e.right.body, Binary) and e.right.body.op == "and"
    assert unparse(parse_expr("not forall x in xs: x > 0")) == "not (forall x in xs: (x > 0))"


# Regresión (2026-09-05): `if` y `match` como operando perdían los paréntesis al reimprimir.
# `(if c then 1 else 2) > 3` salía como `if c then 1 else 2 > 3` (otro programa, E400) y
# `a or (match r {...})` no volvía a parsear (E000). Los mutantes del cuerpo se construyen
# reimprimiendo, así que 162 mutantes de la quinta corrida murieron por el reimpresor.
@pytest.mark.parametrize("src", [
    "(if c then 1 else 2) > 3",
    "x + (if c then 1 else 2) * 2",
    "a or (match r { None => false Some(v) => v > 1 })",
    "not (match r { None => false Some(v) => v > 1 })",
    "-(if c then 1 else 2)",
    "if (if a then b else c) then 1 else 2",
    # 2026-09-05: el cuantificador también se parsea hasta el final; `(forall x in xs: x > 0) and
    # result == 0` volvía como `forall x in xs: (x > 0) and (result == 0)`, y el almacén lo certificaba.
    "(forall x in xs: x > 0) and result == 0",
    "(exists v in xs: v == 1) or q",
    "(not forall x in xs: x > 0) and q",
    "p and (forall x in xs: x > 0) or q",
    # 2026-09-05 (noche), encontrados por el test de propiedad: `not` liga más flojo que los
    # operadores binarios, y un texto con salto de línea se imprimía con el salto literal.
    "(not a) == b",
    "-(not a)",
    "not (not a)",
    'f("a\\nb\\t\\"c\\\\")',
    "forall x in (if c then xs else ys): x > 0",
])
def test_reimprimir_hace_ida_y_vuelta(src):
    e = parse_expr(src)
    otra_vez = parse_expr(unparse(e))
    assert unparse(otra_vez) == unparse(e)
