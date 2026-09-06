"""Dafny -> Sello (bench/vericoding/traducir.py): lo que se traduce, cómo, y lo que no cabe.

Lógica del experimento: si el traductor inlineara mal un helper (captura de variables), o
tradujera `==>` o una comparación encadenada con otro sentido, la medición de la fase 4
mediría un contrato que no es el del benchmark.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench" / "vericoding"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench"))
import traducir as T  # noqa: E402

from sello.compile import check_source  # noqa: E402
from sello.pretty import unparse_fn  # noqa: E402


def spec(preambulo: str, metodo: str) -> str:
    return (f"// <vc-preamble>\n{preambulo}\n// </vc-preamble>\n\n// <vc-helpers>\n// </vc-helpers>\n\n"
            f"// <vc-spec>\n{metodo}\n// </vc-spec>\n// <vc-code>\n{{\n  assume {{:axiom}} false;\n}}\n// </vc-code>\n")


def texto(dafny: str, id_: str = "DX0000") -> str:
    tarea, motivos, _ = T.traducir(id_, dafny)
    assert tarea is not None, motivos
    return T.contrato(tarea).texto


def test_inlinea_predicados_parte_conjunciones_y_traduce_implicacion_y_cadenas():
    d = spec("predicate ValidInput(n: int, k: int) { 1 <= n <= 100 && k > 0 }\n"
             "predicate Small(n: int) { n < 10 }",
             "method solve(n: int, k: int) returns (result: int)\n"
             "  requires ValidInput(n, k)\n"
             "  ensures Small(n) ==> result == n * k\n"
             "  ensures result >= 0 <==> n >= 0")
    t = texto(d)
    assert "requires (1 <= n)\n  requires (n <= 100)\n  requires (k > 0)" in t
    assert "ensures ((not (n < 10)) or (result == (n * k)))" in t
    assert "ensures ((result >= 0) == (n >= 0))" in t
    assert "ValidInput" not in t and "Small" not in t
    assert t.rstrip().endswith("{\n" + T.ct.HUECO + "\n}")
    assert T.ct.EJEMPLOS in t and "example" not in t.split("# add")[0].replace("effects", "")


def test_secuencias_cuantificadores_con_dominio_y_var():
    d = spec("predicate AllPos(s: seq<int>) { forall x :: x in s ==> x > 0 }\n"
             "predicate Has(s: seq<int>, v: int) { exists y | y in s :: y == v }\n"
             "function Twice(s: seq<int>): seq<int> { var t := s + s; t }",
             "method f(xs: seq<int>, v: int) returns (r: seq<int>)\n"
             "  requires AllPos(xs) && v !in xs\n"
             "  ensures |r| == 2 * |xs| && Has(r, v) && r == Twice(xs)")
    t = texto(d)
    assert "requires forall x in xs: (x > 0)" in t
    assert "requires not contains(xs, v)" in t
    assert "ensures (len(result) == (2 * len(xs)))" in t
    assert "ensures exists y in result: (y == v)" in t
    assert "ensures (result == (xs ++ xs))" in t


def test_inlining_sin_captura_de_variables():
    # `P(y)` mete `y` (libre en el argumento) dentro de un `exists y`: la ligada se renombra
    d = spec("predicate P(x: int, s: seq<int>) { exists y :: y in s && y > x }",
             "method f(y: int, s: seq<int>) returns (r: bool)\n  requires |s| > 0\n  ensures r == P(y, s)")
    t = texto(d)
    assert "exists y_1 in s: (y_1 > y)" in t


def test_nat_y_requires_vacio():
    d = spec("", "method f(n: nat, s: seq<nat>) returns (r: nat)\n  ensures r == n")
    tarea, motivos, notas = T.traducir("DX0001", spec("", "method f(n: nat, s: seq<nat>) returns (r: nat)\n  ensures r == n"))
    t = T.contrato(tarea).texto
    assert "requires (n >= 0)\n  requires forall x in s: (x >= 0)" in t
    assert "ensures (result == n)\n  ensures (result >= 0)" in t
    assert "nat" in notas and "requires vacío" not in notas
    tarea2, _, notas2 = T.traducir("DX0002", spec("", "method g(xs: seq<int>) returns (r: int)\n  ensures r == |xs|"))
    assert "requires (len(xs) >= 0)" in T.contrato(tarea2).texto and "requires vacío" in notas2


def test_helper_recursivo_congelado_con_definicion_en_ensures_y_ejemplos_calculados():
    d = spec("function power(b: int, e: int): int\n  requires e >= 0\n  decreases e\n"
             "{ if e == 0 then 1 else b * power(b, e - 1) }",
             "method f(b: int, e: int) returns (r: int)\n  requires e >= 0\n  ensures r == power(b, e)")
    tarea, motivos, _ = T.traducir("DX0003", d)
    assert tarea is not None, motivos
    t = T.contrato(tarea).texto
    assert tarea.helpers == ["power"]
    assert "fn power(b: Int, e: Int) -> Int\n  requires (e >= 0)\n  ensures (result == (if (e == 0) then 1 else (b * power(b, (e - 1)))))" in t
    assert "example (power(0, 0) == 1)" in t and t.count("example (power(") == 2
    assert "ensures (result == power(b, e))" in t
    # el helper congelado compila solo, pasa sus ejemplos y el probador lo certifica en nivel 2
    r = check_source(unparse_fn(T.contrato(tarea).helpers[0]))
    assert r["ok"] and r["functions"][0]["level"] == 2


def test_abs_supuesto_y_nota_div():
    d = spec("", "method f(a: int, b: int) returns (r: int)\n  requires b != 0\n  ensures r == abs(a) / b")
    tarea, _, notas = T.traducir("DX0004", d)
    assert "ensures (result == ((if (a >= 0) then a else -a) / b))" in T.contrato(tarea).texto
    assert "función supuesta: abs" in notas and "div" in notas


@pytest.mark.parametrize("preambulo, metodo, motivo", [
    ("", "method f(s: seq<int>) returns (r: int)\n  requires |s| > 0\n  ensures r == s[0]", "índice s[i]"),
    ("", "method f(s: seq<int>) returns (r: int)\n  ensures forall i :: 0 <= i < |s| ==> r >= 0", "cuantificador sobre enteros"),
    ("", "method f(a: array<int>) returns (r: int)\n  ensures r >= 0", "tipo: array"),
    ("", "method f(x: real) returns (r: real)\n  ensures r >= x", "tipo: real"),
    ("", "method f(x: int) returns (r: int, q: int)\n  ensures r >= x", "varios valores de retorno"),
    ("", "method f(x: int) returns (r: int)\n  requires x > 0", "sin ensures"),
    ("", "method f(x: int) returns (r: int)\n  ensures r == g(x)", "función sin definir: g"),
    ("function len(s: seq<int>): int { if s == [] then 0 else 1 + len(s[1..]) }",
     "method f(s: seq<int>) returns (r: int)\n  ensures r == len(s)", "tramo s[i..j]"),
])
def test_lo_que_no_cabe_dice_por_que(preambulo, metodo, motivo):
    tarea, motivos, _ = T.traducir("DX0009", spec(preambulo, metodo))
    assert tarea is None and motivo in motivos, motivos


def test_nombres_reservados_se_renombran():
    d = spec("", "method sorted(count: int, result: int) returns (r: int)\n  requires count > 0\n  ensures r == count + result")
    t = texto(d)
    assert "fn sorted_(count_: Int, result_: Int) -> Int" in t
    assert "ensures (result == (count_ + result_))" in t


def test_resumen_de_cobertura_cuenta_por_fuente_y_motivo():
    filas = [
        {"id": "DA0001", "source": "apps", "cabe": True, "motivos": [], "notas": ["div"], "helpers": [], "longitud": 100},
        {"id": "DA0002", "source": "apps", "cabe": False, "motivos": ["tipo: array", "índice s[i]"], "notas": [], "helpers": [], "longitud": 0},
        {"id": "DD0001", "source": "dafnybench", "cabe": False, "motivos": ["índice s[i]"], "notas": [], "helpers": [], "longitud": 0},
    ]
    md = T.resumen(filas, "hoy")
    assert "| **caben** | **1** (50 %) | **0** (0 %) | **1** (33 %) |" in md
    assert "| tipo no soportado | 1 | 1 |" in md
    assert "| índice s[i] | 2 | 1 |" in md
    assert "- tipo: array: 1" in md
