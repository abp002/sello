"""El contrato escrito por otro: qué se congela y qué se rechaza.

Lógica del experimento: si el extractor dejara pasar un helper de implementación, haiku
recibiría medio cuerpo hecho; si `violacion` no viera un `ensures` debilitado, la métrica
mediría un contrato que ya no es el de sonnet.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench"))
import contrato as ct  # noqa: E402

SONNET = """
fn head(xs: List[Int]) -> Int
  requires len(xs) >= 1
  ensures contains(xs, result)
  effects pure
  example head([5]) == 5
{ match xs { [] => 0  [h, ..t] => h } }

fn is_ok(xs: List[Int], v: Int) -> Bool
  requires len(xs) >= 1
  ensures result or head(xs) != v
  effects pure
  example is_ok([1], 1) == true
{ head(xs) == v }

fn max2(a: Int, b: Int) -> Int
  requires a >= 0
  ensures result >= a and result >= b
  effects pure
  example max2(1, 2) == 2
{ if a >= b then a else b }

fn best(xs: List[Int]) -> Int
  requires len(xs) >= 1
  ensures is_ok(xs, result)
  effects pure
  example best([3, 1]) == 3
{ match xs { [] => 0  [h, ..t] => max2(h, 0) } }
"""


def test_extrae_helpers_alcanzables_desde_las_clausulas_y_no_los_de_implementacion():
    c = ct.extraer(SONNET, "best")
    assert c.nombres == ["head", "is_ok"]  # `head` llega a través de `is_ok`; `max2` solo lo usa el cuerpo
    assert "max2" not in c.texto
    assert "match xs" not in c.texto.split("fn best")[1]  # la principal va sin cuerpo
    assert c.texto.rstrip().endswith("{\n" + ct.HUECO + "\n}")
    assert "ensures is_ok(xs, result)" in c.texto and "example (best([3, 1]) == 3)" in c.texto


def test_cabecera_es_todo_menos_el_cuerpo():
    c = ct.extraer(SONNET, "best")
    assert ct.cabecera(c.principal) == ("fn best(xs: List[Int]) -> Int\n  requires (len(xs) >= 1)\n"
                                        "  ensures is_ok(xs, result)\n  effects pure\n  example (best([3, 1]) == 3)")


def _con_cuerpo(cuerpo: str, extra: str = "") -> str:
    c = ct.extraer(SONNET, "best")
    return c.texto.replace(ct.HUECO, "  " + cuerpo) + ("\n\n" + extra if extra else "")


def test_acepta_un_cuerpo_nuevo_y_helpers_propios():
    c = ct.extraer(SONNET, "best")
    code = _con_cuerpo("mine(xs)", "fn mine(xs: List[Int]) -> Int\n  requires len(xs) >= 1\n  ensures contains(xs, result)\n"
                                    "  effects pure\n  example mine([3]) == 3\n{ head(xs) }")
    assert ct.violacion(c, code) is None


def test_rechaza_ensures_debilitado_helper_cambiado_o_ausente():
    c = ct.extraer(SONNET, "best")
    debil = _con_cuerpo("head(xs)").replace("ensures is_ok(xs, result)", "ensures result >= 0")
    assert "`best`" in (ct.violacion(c, debil) or "")
    tocado = _con_cuerpo("head(xs)").replace("  (head(xs) == v)\n", "  true\n")
    assert "`is_ok`" in (ct.violacion(c, tocado) or "")
    sin_head = _con_cuerpo("0")
    sin_head = sin_head[sin_head.index("fn is_ok"):]
    assert "`head`" in (ct.violacion(c, sin_head) or "")
    assert "`best`" in (ct.violacion(c, "fn other(n: Int) -> Int\n  requires n >= 0\n  ensures result == n\n  effects pure\n  example other(1) == 1\n{ n }") or "")


def test_el_formato_no_cuenta_y_lo_que_no_parsea_lo_dice_el_compilador():
    c = ct.extraer(SONNET, "best")
    reformateado = _con_cuerpo("head(xs)").replace("  requires (len(xs) >= 1)\n  ensures is_ok(xs, result)",
                                                    "  requires   len(xs)>=1\n  ensures is_ok( xs , result )")
    assert ct.violacion(c, reformateado) is None
    assert ct.violacion(c, "fn best(") is None
