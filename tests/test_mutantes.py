"""Mutantes del cuerpo: los operadores no tocan el contrato y la clasificación no miente.

Lógica del experimento, como test_juez: si el mutador tocara un `ensures` o la regla de
destinos se torciera, la métrica mentiría.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench"))
import juez  # noqa: E402
import mutantes as mu  # noqa: E402

from sello.parser import parse  # noqa: E402
from sello.pretty import unparse  # noqa: E402

SELLO = """
fn factorial(n: Int) -> Int
  requires n >= 0
  ensures result >= 1
  effects pure
  example factorial(5) == 120
{ if n == 0 then 1 else n * factorial(n - 1) }

fn first_over(xs: List[Int], d: Int) -> Int
  requires d >= 0
  ensures result >= d
  ensures forall x in xs: x <= 100
  effects pure
  example first_over([], 3) == 3
{ match xs { [] => d  [h, ..t] => if h > d then h else first_over(t, d) } }
"""

PY = '''
def f(n):
    assert n >= 0, "pre"
    r = n - 1
    assert r >= -1
    return r
'''


def contrato(src: str) -> list:
    return [(f.name, [unparse(r) for r in f.requires], [unparse(e) for e in f.ensures], [unparse(x) for x in f.examples])
            for f in parse(src).fns]


# ---------- Sello ----------

def test_sello_no_toca_el_contrato_y_cada_mutante_es_distinto():
    canon, muts = mu.mutar("sello", SELLO)
    assert muts
    assert len({m["code"] for m in muts}) == len(muts)
    for m in muts:
        assert m["code"] != canon
        assert contrato(m["code"]) == contrato(canon), m["desc"]


def test_sello_genera_los_bugs_tipicos():
    _, muts = mu.mutar("sello", SELLO)
    descs = {(m["fn"], m["op"], m["desc"]) for m in muts}
    assert ("factorial", "frontera", "(n == 0) -> (n != 0)") in descs
    assert ("factorial", "aritmetica", "(n - 1) -> (n + 1)") in descs
    assert ("factorial", "aritmetica", "(n * factorial((n - 1))) -> (n + factorial((n - 1)))") in descs
    assert ("factorial", "literal", "1 -> 2") in descs and ("factorial", "literal", "1 -> 0") in descs
    assert ("factorial", "ramas",
            "if (n == 0) then 1 else (n * factorial((n - 1))) -> if (n == 0) then (n * factorial((n - 1))) else 1") in descs
    assert ("first_over", "argumentos", "first_over(t, d) -> first_over(d, t)") in descs
    assert ("first_over", "variable", "h -> d") in descs      # variable del patrón por parámetro
    assert ("first_over", "variable", "d -> xs") in descs     # y al revés, aunque no tipe
    assert not any(m["op"] == "variable" and "_" in m["desc"].split(" -> ") for m in muts)


def test_sello_solo_muta_el_cuerpo_nunca_el_forall_del_contrato():
    _, muts = mu.mutar("sello", SELLO)
    assert not any("100" in m["desc"] or "<= 100" in m["desc"] for m in muts)


# ---------- Python ----------

def test_python_no_toca_los_assert():
    canon, muts = mu.mutar("python_asserts", PY)
    asserts = lambda src: [ast.unparse(a) for a in ast.walk(ast.parse(src)) if isinstance(a, ast.Assert)]  # noqa: E731
    assert muts
    for m in muts:
        assert asserts(m["code"]) == asserts(canon), m["desc"]
    descs = {m["desc"] for m in muts}
    assert "n - 1 -> n + 1" in descs
    assert "n -> r" in descs                   # variable: parámetro por asignada
    assert "1 -> 2" in descs and "1 -> 0" in descs


def test_python_intercambia_ramas_y_argumentos():
    src = "def g(a, b):\n    if a < b:\n        return h(a, b)\n    else:\n        return 0\n\ndef h(x, y):\n    return x - y\n"
    _, muts = mu.mutar("python", src)
    ops = {(m["fn"], m["op"]) for m in muts}
    assert ("g", "ramas") in ops and ("g", "argumentos") in ops and ("g", "frontera") in ops
    assert ("h", "aritmetica") in ops and ("h", "variable") in ops


# ---------- destinos ----------

OK, WRONG, CAUGHT, REJECT = juez.OK, juez.WRONG, juez.CAUGHT, juez.REJECT


@pytest.mark.parametrize("juez_ok,señal,dominio,esperado", [
    (False, "E400", [], mu.NO_COMPILA),
    (False, "E404", [], mu.NO_COMPILA),
    (False, "E200", [], mu.MUERTO),        # ejemplos propios
    (False, "wrong", [], mu.MUERTO),       # caso visible
    (False, "E201", [], mu.MUERTO),        # el contrato, dentro del bucle
    (False, "E500", [], mu.MUERTO),
    (False, "timeout", [], mu.MUERTO),
    (True, None, [OK, OK], mu.EQUIVALENTE),
    (True, None, [], mu.EQUIVALENTE),
    (True, None, [OK, WRONG, CAUGHT], mu.SILENCIOSO),   # una silenciosa manda
    (True, None, [OK, CAUGHT, REJECT], mu.CAZADO),
    (True, None, [OK, REJECT], mu.RUIDOSO),
])
def test_clasificar(juez_ok, señal, dominio, esperado):
    assert mu.clasificar(juez_ok, señal, dominio) == esperado


@pytest.mark.parametrize("señal,esperado", [
    ("E200", mu.EJEMPLOS), ("wrong", mu.EJEMPLOS),
    ("E201", mu.CONTRATO), ("assert", mu.CONTRATO),
    ("E300", mu.FRONTERA), ("E500", mu.FRONTERA), ("raise", mu.FRONTERA), ("timeout", mu.FRONTERA), ("load", mu.FRONTERA),
])
def test_causa_muerte(señal, esperado):
    assert mu.causa_muerte(señal) == esperado


def test_contar_solo_suma_llamadas_de_los_que_llegan():
    d = lambda ok=0, wrong=0, caught=0, reject=0: {OK: ok, WRONG: wrong, CAUGHT: caught, REJECT: reject}  # noqa: E731
    muts = [
        {"op": "literal", "cat": mu.MUERTO, "muerte": mu.EJEMPLOS, "dom": d(), "amb": d()},
        {"op": "literal", "cat": mu.MUERTO, "muerte": mu.CONTRATO, "dom": d(), "amb": d()},
        {"op": "frontera", "cat": mu.NO_COMPILA, "muerte": None, "dom": d(), "amb": d()},
        {"op": "frontera", "cat": mu.EQUIVALENTE, "muerte": None, "dom": d(ok=5), "amb": d()},
        {"op": "ramas", "cat": mu.SILENCIOSO, "muerte": None, "dom": d(ok=2, wrong=2, caught=1), "amb": d(wrong=9)},
        {"op": "variable", "cat": mu.CAZADO, "muerte": None, "dom": d(ok=2, caught=3), "amb": d()},
        {"op": "variable", "cat": mu.RUIDOSO, "muerte": None, "dom": d(reject=1), "amb": d()},
    ]
    k = mu.contar(muts)
    assert k["generados"] == 7 and k["llegan"] == 3
    assert k[mu.MUERTO] == 2 and k["muerto_ejemplos"] == 1 and k["muerto_contrato"] == 1
    assert k["llamadas_wrong"] == 2 and k["llamadas_caught"] == 4   # la zona ambigua no cuenta
    assert k["silencioso_por_op"]["ramas"] == 1 and k["llegan_por_op"]["variable"] == 2
