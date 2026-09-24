"""El probador (nivel 2): lo que promete y lo que nunca hace.

Prueba lo verdadero (certificado de nivel 2), encuentra entradas que rompen el contrato y las
confirma ejecutándolas (el error de siempre, con la entrada), y nunca rechaza por un
contraejemplo que el intérprete no reproduce ni por una prueba que no le sale.
"""

from __future__ import annotations

import subprocess

import pytest
import z3
from conftest import fails_with
from hypothesis import given, settings
from hypothesis import strategies as st

from sello import prover as pr
from sello.compile import check_source, compile_source, run_examples
from sello.interp import NONE, Some
from sello.nodes import INT, TEXT, TList, TOption


def verdict(src: str, name: str | None = None) -> pr.Verdict:
    program, interp = compile_source(src)
    run_examples(program, interp)
    fn = program.fns[0] if name is None else next(f for f in program.fns if f.name == name)
    return pr.prove(program, fn, interp, pr.Budget())


FACT = """
fn factorial(n: Int) -> Int
  requires n >= 0
  ensures result >= 1
  effects pure
  example factorial(0) == 1
  example factorial(5) == 120
{ if n == 0 then 1 else n * factorial(n - 1) }
"""

CLAMP_MAL = """
fn clamp(x: Int, lo: Int, hi: Int) -> Int
  requires lo <= hi
  ensures x < lo or x > hi or result == x
  ensures x >= lo or result == lo
  ensures x <= hi or result == hi
  effects pure
  example clamp(5, 1, 10) == 5
  example clamp(1, 1, 10) == 1
{ if x < lo then hi else if x > hi then lo else x }
"""


# ---------- probada ----------

def test_factorial_se_prueba_con_su_propio_contrato_como_hipotesis():
    assert verdict(FACT).status == pr.PROVEN


def test_recursion_sobre_listas_con_medida_de_longitud():
    src = """
fn drop(xs: List[Int], k: Int) -> List[Int]
  requires k >= 0 and k <= len(xs)
  ensures len(result) == len(xs) - k
  effects pure
  example drop([1, 2, 3], 1) == [2, 3]
  example drop([1, 2, 3], 3) == []
{ if k == 0 then xs else match xs { [] => [] [_, ..t] => drop(t, k - 1) } }
"""
    assert verdict(src).status == pr.PROVEN


def test_count_del_contrato_es_la_funcion_recursiva_de_z3():
    src = """
fn count_of(xs: List[Int], x: Int) -> Int
  requires len(xs) >= 0
  ensures result == count(xs, x)
  effects pure
  example count_of([1, 2, 2, 3], 2) == 2
{ match xs { [] => 0 [h, ..t] => if h == x then 1 + count_of(t, x) else count_of(t, x) } }
"""
    assert verdict(src).status == pr.PROVEN


def test_option_y_match_en_el_ensures():
    src = """
fn nth(xs: List[Int], i: Int) -> Option[Int]
  requires i >= 0
  ensures i < len(xs) or result == None
  ensures i >= len(xs) or result != None
  effects pure
  example nth([4, 5], 1) == Some(5)
  example nth([4, 5], 2) == None
{ match xs { [] => None [h, ..t] => if i == 0 then Some(h) else nth(t, i - 1) } }
"""
    assert verdict(src).status == pr.PROVEN


def test_check_source_da_el_nivel_y_cuenta_las_probadas():
    r = check_source(FACT)
    assert r["proven"] == 1 and r["functions"][0]["level"] == 2 and "unproven" not in r["functions"][0]


# ---------- contraejemplo real ----------

def test_contraejemplo_real_es_E201_con_la_entrada_y_por_el_pipeline_entero():
    v = verdict(CLAMP_MAL)
    assert v.status == pr.COUNTEREXAMPLE
    e = v.error
    assert e.code == "E201" and e.extra["found_by"] == "prover" and e.extra["input"].startswith("clamp(")
    assert "found by the prover" in e.to_dict()["what"]
    e2 = fails_with(CLAMP_MAL, "E201")  # proceso hijo incluido
    assert e2.extra["found_by"] == "prover" and e2.function == "clamp"


def test_llamada_que_viola_requires_para_alguna_entrada_es_E300():
    src = """
fn g(n: Int) -> Int
  requires n >= 0
  ensures result == n
  effects pure
  example g(1) == 1
{ n }

fn f(n: Int) -> Int
  requires n >= 0
  ensures result == n - 1
  effects pure
  example f(5) == 4
{ g(n - 1) }
"""
    v = verdict(src, "f")
    assert v.status == pr.COUNTEREXAMPLE and v.error.code == "E300" and v.error.extra["input"] == "f(0)"


def test_division_por_cero_para_alguna_entrada_es_E500():
    src = """
fn f(a: Int, b: Int) -> Int
  requires b >= 0
  ensures result * (b - 1) <= a or b == 1
  effects pure
  example f(4, 3) == 2
{ a / (b - 1) }
"""
    v = verdict(src)
    assert v.status == pr.COUNTEREXAMPLE and v.error.code == "E500" and "division by zero" in v.error.detail


def test_el_ejemplo_del_repo_tenia_un_bug_que_el_probador_encuentra():
    """`div` de ejemplos/basicos.sello decía `result * b <= a`, falso con divisor negativo."""
    src = """
fn div(a: Int, b: Int) -> Int
  requires b != 0
  ensures result * b <= a
  effects pure
  example div(7, 2) == 3
  example div(-7, 2) == -4
{ a / b }
"""
    v = verdict(src)
    assert v.status == pr.COUNTEREXAMPLE and v.error.code == "E201"
    assert check_source(open("ejemplos/basicos.sello").read())["ok"]


# ---------- nunca rechaza por su cuenta ----------

def test_contraejemplo_que_el_interprete_no_reproduce_no_rechaza():
    """El contrato de `g` es más débil que su cuerpo: Z3 cree que f(0) puede dar 1, pero da 6."""
    src = """
fn g(n: Int) -> Int
  requires n >= 0
  ensures result >= 0
  effects pure
  example g(0) == 5
{ n + 5 }

fn f(n: Int) -> Int
  requires n >= 0
  ensures result >= 2
  effects pure
  example f(0) == 6
{ g(n) + 1 }
"""
    assert verdict(src, "f").status == pr.UNKNOWN
    r = check_source(src)
    assert r["ok"] and r["functions"][1]["level"] == 1 and r["functions"][1]["unproven"]


def test_recursion_sin_medida_que_decrezca_no_es_nivel_2():
    src = """
fn f(n: Int) -> Int
  requires n >= 0
  ensures result == 42
  effects pure
  example f(0) == 42
{ if n == 0 then 42 else f(n) }
"""
    v = verdict(src)
    assert v.status == pr.UNKNOWN and v.reason.startswith("termination")


def test_recursion_mutua_no_es_nivel_2():
    src = """
fn par(n: Int) -> Bool
  requires n >= 0
  ensures result or not result
  effects pure
  example par(2) == true
{ if n == 0 then true else impar(n - 1) }

fn impar(n: Int) -> Bool
  requires n >= 0
  ensures result or not result
  effects pure
  example impar(1) == true
{ if n == 0 then false else par(n - 1) }
"""
    v = verdict(src, "par")
    assert v.status == pr.UNKNOWN and v.reason.startswith("mutual recursion")


def test_sin_tiempo_es_unknown_no_error():
    program, interp = compile_source(CLAMP_MAL)
    budget = pr.Budget(program_ms=0)
    v = pr.prove(program, program.fns[0], interp, budget)
    assert v.status == pr.UNKNOWN and v.error is None


def test_si_el_hijo_no_responde_lo_que_falta_queda_unknown(monkeypatch):
    program, _ = compile_source(FACT + CLAMP_MAL.replace("clamp", "otra"))

    def run(*a, **k):
        raise subprocess.TimeoutExpired(a[0], 1, output=b'{"name": "factorial", "status": "proven", "reason": "", "ms": 3, "error": null}\n')
    monkeypatch.setattr(pr.subprocess, "run", run)
    vs = pr.prove_program(program)
    assert vs["factorial"].status == pr.PROVEN
    assert vs["otra"].status == pr.UNKNOWN and "did not answer" in vs["otra"].reason


# ---------- piezas ----------

def test_valores_del_modelo_vuelven_al_interprete():
    ctx = z3.Context()
    xs = z3.Const("xs", z3.SeqSort(z3.IntSort(ctx)))
    empty = z3.Const("e", z3.SeqSort(z3.IntSort(ctx)))
    t = z3.Const("t", z3.StringSort(ctx))
    opt = z3.Datatype("Option[Int]", ctx); opt.declare("None"); opt.declare("Some", ("val", z3.IntSort(ctx))); opt = opt.create()
    o, o2 = z3.Const("o", opt), z3.Const("o2", opt)
    s = z3.Solver(ctx=ctx)
    s.add(xs == z3.Concat(z3.Unit(z3.IntVal(1, ctx)), z3.Unit(z3.IntVal(-2, ctx))), z3.Length(empty) == 0,
          t == z3.StringVal("hi", ctx), o == opt.constructor(1)(z3.IntVal(3, ctx)), o2 == opt.constructor(0)())
    assert s.check() == z3.sat
    m = s.model()
    ev = lambda c: m.eval(c, model_completion=True)  # noqa: E731
    assert pr.value(ev(xs), TList(INT)) == [1, -2]
    assert pr.value(ev(empty), TList(INT)) == []
    assert pr.value(ev(t), TEXT) == "hi"
    assert pr.value(ev(o), TOption(INT)) == Some(3) and pr.value(ev(o2), TOption(INT)) is NONE


@settings(max_examples=200, deadline=None)
@given(a=st.integers(-60, 60), b=st.integers(-9, 9).filter(lambda b: b != 0))
def test_la_division_de_z3_redondea_como_python(a, b):
    q = z3.simplify(pr.floordiv(z3.IntVal(a), z3.IntVal(b)))
    assert q.as_long() == a // b
    assert z3.simplify(z3.IntVal(a) - z3.IntVal(b) * q).as_long() == a % b


@pytest.mark.parametrize("v, big", [(10, False), ([1, 2], False), (10 ** 7, True), ([Some(10 ** 7)], True), (list(range(65)), True)])
def test_un_contraejemplo_enorme_no_se_ejecuta(v, big):
    assert pr.too_big(v) is big


INSATISFACIBLE = """
fn q(x: Int, y: Int) -> Int
  requires x >= 0 and y >= 0 and y - x > 2
  ensures x < result * result and result * result < y
  effects pure
  example q(0, 4) == 1
{ find_value(x, y, 1) }

fn find_value(x: Int, y: Int, r: Int) -> Int
  requires r >= 1 and x >= 0 and y >= 0 and y - x > 2
  ensures x < result * result and result * result < y
  effects pure
  example find_value(0, 4, 1) == 1
{ if r * r > x and r * r < y then r else find_value(x, y, r + 1) }
"""


def test_una_spec_insatisfacible_en_un_punto_no_prueba_cualquier_cosa():
    # Vericoding DD0435 (2026-09-06): para `(1, 4)` no hay entero entre 1 y 4 al cuadrado, así que
    # el contrato de `find_value` como axioma `forall` era inconsistente y Z3 «probaba» todo,
    # incluida la terminación de una recursión en la que `r` solo crece (`q(1, 4)` no termina).
    # La hipótesis de inducción solo vale en cada llamada, bajo su camino, y la terminación se
    # prueba sin ella.
    v = verdict(INSATISFACIBLE, "find_value")
    assert v.status == pr.UNKNOWN and v.reason.startswith("termination")
    d = check_source(INSATISFACIBLE)
    assert {f["name"]: f["level"] for f in d["functions"]} == {"q": 2, "find_value": 1}


MAXI = """
fn maxi(xs: List[Int]) -> Int
  requires len(xs) > 0
  ensures forall i in 0..len(xs): xs[i] <= result
  ensures exists i in 0..len(xs): xs[i] == result
  effects pure
  example maxi([3, 9, 2]) == 9
  example maxi([1]) == 1
{ match xs { [] => 0  [h, ..t] => if is_empty(t) then h else if h >= maxi(t) then h else maxi(t) } }

fn is_empty(t: List[Int]) -> Bool
  requires 1 == 1
  ensures result == (len(t) == 0)
  effects pure
  example is_empty([]) == true
{ match t { [] => true  [_, .._] => false } }
"""


def test_el_cuantificador_sobre_un_rango_con_indice_se_prueba_en_nivel_2():
    """ALE-108: la forma `forall i :: 0 <= i < |s| ==> P(s[i])` de Dafny, en Sello."""
    r = check_source(MAXI)
    assert r["ok"] and r["proven"] == 2, r


def test_un_ensures_falso_con_indice_da_el_contraejemplo_y_un_indice_fuera_de_rango_es_E500():
    first = ("fn first(xs: List[Int]) -> Int\n  requires len(xs) > 0\n"
             "  ensures forall i in 0..len(xs): xs[i] >= result\n  effects pure\n"
             "  example first([1, 2]) == 1\n{ match xs { [] => 0  [h, .._] => h } }")
    e = fails_with(first, "E201")
    assert e.extra["found_by"] == "prover" and e.extra["input"].startswith("first([")
    # `xs[0]` en un ensures con `requires 1 == 1`: los ejemplos no pasan por `[]`, el probador sí.
    src = ("fn f(xs: List[Int]) -> Int\n  requires 1 == 1\n  ensures xs[0] >= 0 or true\n"
           "  effects pure\n  example f([1]) == 0\n{ 0 }")
    e = fails_with(src, "E500")
    assert e.extra["found_by"] == "prover" and "f([])" in e.extra["input"]


def test_el_veredicto_de_una_funcion_no_depende_de_las_que_la_preceden():
    """ALE-171: en basicos.sello, Z3 5.1 revienta por dentro probando `dedupe` (UNREACHABLE) y el
    proceso segfaulteaba en la siguiente, así que `contains_in` salía nivel 1 en el fichero y
    nivel 2 sola. El veredicto de cada función en el programa es el de probarla sola."""
    from pathlib import Path
    from sello.parser import parse
    from sello.prover import prove_program
    program = parse((Path(__file__).resolve().parents[1] / "ejemplos" / "basicos.sello").read_text())
    juntas = prove_program(program)
    for fn in program.fns:
        sola = prove_program(program, only={fn.name})[fn.name]
        assert juntas[fn.name].status == sola.status, (fn.name, juntas[fn.name], sola)


# ---------- fase u: `/` y `%` con divisor variable (ALE-169) ----------

PRIMO = """
fn no_divisor(n: Int, k: Int) -> Bool
  requires n >= 2
  requires k >= 2
  requires k <= n
  ensures result == (forall j in k..n: n % j != 0)
  effects pure
  example no_divisor(7, 2) == true
  example no_divisor(9, 2) == false
{ if k == n then true else if n % k == 0 then false else no_divisor(n, k + 1) }
"""


def test_la_primalidad_por_recursion_se_prueba_con_modulo_no_interpretado():
    """Lo exacto (`n - j * (n / j)`, no lineal) dejaba esta obligación sin decidir."""
    assert verdict(PRIMO).status == pr.PROVEN


def test_la_fase_u_no_prueba_una_afirmacion_falsa_sobre_el_modulo():
    """Los axiomas de la fase u son verdaderos: lo falso no se prueba. `n % k` puede valer
    k - 1 (n = 5, k = 3), así que este ensures es falso y el cuerpo lo incumple."""
    src = """
fn f(n: Int, k: Int) -> Bool
  requires n >= 0
  requires k >= 2
  ensures result == (n % k < k - 1)
  effects pure
  example f(4, 3) == true
{ true }
"""
    v = verdict(src)
    assert v.status != pr.PROVEN
    assert v.status == pr.COUNTEREXAMPLE or v.status == pr.UNKNOWN


def test_la_fase_u_respeta_el_signo_del_divisor():
    """Con divisor negativo el resto de Sello (como Python) es <= 0: `n % k >= 0` es falso."""
    src = """
fn g(n: Int, k: Int) -> Bool
  requires k <= -1
  ensures result == true
  ensures n % k >= 0
  effects pure
  example g(4, -1) == true
{ true }
"""
    assert verdict(src).status != pr.PROVEN
