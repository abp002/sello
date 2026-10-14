"""¿El contrato fija una sola respuesta? (SEL-8)

Z3 busca una entrada que cumpla `requires` y dos resultados distintos que cumplan los dos el
`ensures`. Si no hay (`unique`), dos cuerpos que cumplan el contrato devuelven lo mismo; si hay
y el intérprete confirma los dos resultados (`ambiguous`), sale el testigo. Lo que llaman las
cláusulas se modela por su contrato, como en el nivel 2: un testigo que el intérprete no
confirma no se afirma.
"""

from __future__ import annotations

from sello.compile import compile_source
from sello.interp import Interpreter
from sello.prover import Budget
from sello.unique import AMBIGUOUS, UNIQUE, UNKNOWN, unique


def veredicto(src: str, name: str | None = None):
    program, _ = compile_source(src)
    fn = program.fns[0] if name is None else next(f for f in program.fns if f.name == name)
    return unique(program, fn, Interpreter(program), Budget())


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

# El `ensures` de cotas: lo que dejaba pasar los silenciosos de longest_run.
COTAS = """
fn clamp(x: Int, lo: Int, hi: Int) -> Int
  requires lo <= hi
  ensures result >= lo and result <= hi
  effects pure
  example clamp(5, 0, 10) == 5
{ if x < lo then lo else if x > hi then hi else x }
"""


def test_un_contrato_completo_fija_la_respuesta():
    v = veredicto(CLAMP)
    assert v.status == UNIQUE, v.reason
    assert v.witness is None


def test_un_contrato_de_cotas_no_la_fija_y_da_el_testigo_ejecutado():
    v = veredicto(COTAS)
    assert v.status == AMBIGUOUS, v.reason
    args, r1, r2 = v.witness["args"], v.witness["results"][0], v.witness["results"][1]
    x, lo, hi = args
    assert lo <= hi and r1 != r2
    assert lo <= r1 <= hi and lo <= r2 <= hi
    assert v.witness["input"] == f"clamp({x}, {lo}, {hi})"


def test_listas_y_cuantificadores():
    # «Ordenada» sin decir que conserva los elementos: [] y cualquier otra lista ordenada valen.
    src = """
fn sort(xs: List[Int]) -> List[Int]
  requires len(xs) >= 0
  ensures forall i in 0..len(result) - 1: result[i] <= result[i + 1]
  effects pure
  example sort([]) == []
{ xs }
"""
    v = veredicto(src)
    assert v.status == AMBIGUOUS, v.reason
    for r in v.witness["results"]:
        assert all(r[i] <= r[i + 1] for i in range(len(r) - 1))


def test_option_en_el_resultado():
    src = """
fn first(xs: List[Int]) -> Option[Int]
  requires len(xs) >= 0
  ensures len(xs) > 0 or result == None
  effects pure
  example first([]) == None
{
  match xs {
    [] => None
    [h, .._] => Some(h)
  }
}
"""
    v = veredicto(src)
    assert v.status == AMBIGUOUS, v.reason
    assert len(v.witness["args"][0]) > 0


def test_option_fijado():
    src = """
fn first(xs: List[Int]) -> Option[Int]
  requires len(xs) >= 0
  ensures len(xs) > 0 or result == None
  ensures len(xs) == 0 or result == Some(xs[0])
  effects pure
  example first([]) == None
{
  match xs {
    [] => None
    [h, .._] => Some(h)
  }
}
"""
    v = veredicto(src)
    assert v.status == UNIQUE, v.reason


def test_un_testigo_que_solo_existe_por_el_contrato_de_lo_llamado_no_se_afirma():
    # Por su contrato, `inc` podría no ser inyectiva y entonces dos resultados valdrían; su
    # cuerpo sí lo es y el ensures de `f` fija result == x. El intérprete no confirma ningún
    # testigo: no es ambiguo. Tampoco único, porque eso habla de los contratos.
    src = """
fn inc(y: Int) -> Int
  requires 1 == 1
  ensures result >= y
  effects pure
  example inc(1) == 2
{ y + 1 }

fn f(x: Int) -> Int
  requires 1 == 1
  ensures inc(result) == x + 1
  effects pure
  example f(3) == 3
{ x }
"""
    v = veredicto(src, "f")
    assert v.status == UNKNOWN
    assert v.witness is None


def test_lo_llamado_fijado_por_su_contrato_basta():
    src = """
fn inc(y: Int) -> Int
  requires 1 == 1
  ensures result == y + 1
  effects pure
  example inc(1) == 2
{ y + 1 }

fn f(x: Int) -> Int
  requires 1 == 1
  ensures result == inc(x)
  effects pure
  example f(3) == 4
{ x + 1 }
"""
    assert veredicto(src, "f").status == UNIQUE


def test_un_hueco_se_comprueba_sin_cuerpo():
    src = """
fn doble(n: Int) -> Int
  requires n >= 0
  ensures result == n + n
  effects pure
  example doble(3) == 6
{ sorry }
"""
    assert veredicto(src).status == UNIQUE



def test_una_lista_fijada_elemento_a_elemento_es_unica():
    # Con `xs[i]` no interpretada, «misma longitud y mismos elementos» no da «misma lista» si
    # no se dice: la diferencia entre los dos resultados tiene que estar en una posición.
    src = """
fn copy(xs: List[Int]) -> List[Int]
  requires len(xs) >= 0
  ensures len(result) == len(xs)
  ensures forall i in 0..len(xs): result[i] == xs[i]
  effects pure
  example copy([1]) == [1]
{ xs }
"""
    v = veredicto(src)
    assert v.status == UNIQUE, v.reason


def test_una_lista_con_un_elemento_libre_no_lo_es():
    src = """
fn copy(xs: List[Int]) -> List[Int]
  requires len(xs) >= 0
  ensures len(result) == len(xs)
  ensures forall i in 1..len(xs): result[i] == xs[i]
  effects pure
  example copy([1]) == [1]
{ xs }
"""
    v = veredicto(src)
    assert v.status == AMBIGUOUS, v.reason
    a, b = v.witness["results"]
    assert len(a) == len(b) >= 1 and a[0] != b[0] and a[1:] == b[1:]
