"""El harness de vericoding (bench/vericoding/harness4.py): el veredicto y el recuento no mienten.

Lógica del experimento: si el cierre no excluyera los helpers congelados, un helper del benchmark
en nivel 1 contaría como fallo del modelo; si incluyera solo la principal, un helper propio con
un `ensures` fuerte y un cuerpo sin probar pasaría por certificado.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench" / "vericoding"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench"))
import harness4 as H  # noqa: E402

CODE = """
fn frozen(n: Int) -> Int
  requires n >= 0
  ensures result == (if n == 0 then 0 else 1 + frozen(n - 1))
  effects pure
  example frozen(2) == 2
{ if n == 0 then 0 else 1 + frozen(n - 1) }

fn mine(n: Int) -> Int
  requires n >= 0
  ensures result == n
  effects pure
  example mine(3) == 3
{ frozen(n) }

fn solve(n: Int) -> Int
  requires n >= 0
  ensures result == n
  effects pure
  example solve(3) == 3
{ mine(n) }
"""


def _check(levels: dict[str, int], unproven: dict[str, str] | None = None) -> dict:
    unproven = unproven or {}
    return {"ok": True, "functions": [{"name": n, "level": l, **({"unproven": unproven[n]} if n in unproven else {})}
                                      for n, l in levels.items()]}


def test_cierre_sigue_las_llamadas_y_no_entra_en_los_congelados():
    assert H.cierre(CODE, "solve", {"frozen"}) == {"solve", "mine"}
    assert H.cierre(CODE, "solve", set()) == {"solve", "mine", "frozen"}
    assert H.cierre("fn (", "solve", set()) is None


def test_veredicto_exige_nivel_2_en_todo_el_cierre_menos_los_congelados():
    v = H.veredicto(_check({"frozen": 1, "mine": 2, "solve": 2}, {"frozen": "timeout"}), CODE, "solve", {"frozen"})
    assert v["fase"] == "proven" and v["congelados_sin_probar"] == ["frozen"]
    v = H.veredicto(_check({"frozen": 2, "mine": 1, "solve": 2}, {"mine": "undecided: `ensures (result == n)`"}), CODE, "solve", {"frozen"})
    assert v["fase"] == "unproven" and v["principal"] == 2 and v["sin_probar"] == ["mine"]
    assert v["motivos"] == {"mine": "undecided: `ensures (result == n)`"}
    v = H.veredicto({"ok": False, "error": {"code": "E201"}}, CODE, "solve", set())
    assert v["fase"] == "compile" and v["error"]["code"] == "E201"


def test_resumen_cuenta_probadas_aceptadas_y_motivos():
    base = {"source": "apps", "cond": "sello_contrato", "model": "haiku", "helpers": [], "congelados_sin_probar": [],
            "notas": [], "cost": 0.01, "tokens_in": 10, "tokens_out": 5, "thinking": 0, "ms": 100}
    rows = [
        {**base, "problem": "DA0001", "fn": "solve", "accepted_at": 1, "principal_proven_at": 1, "proven_at": 2, "attempts": 2,
         "ultimo_motivo": "", "detail": [{"fase": "unproven", "sello_error": None}, {"fase": "proven", "sello_error": None}]},
        {**base, "problem": "DA0002", "fn": "f", "accepted_at": 2, "principal_proven_at": None, "proven_at": None, "attempts": 3,
         "ultimo_motivo": "timeout: the solver did not answer",
         "detail": [{"fase": "compile", "sello_error": "E400"}, {"fase": "unproven", "sello_error": None}, {"fase": "unproven", "sello_error": None}]},
        {**base, "problem": "DD0003", "source": "dafnybench", "fn": "g", "accepted_at": None, "principal_proven_at": None, "proven_at": None,
         "attempts": 1, "ultimo_motivo": "", "detail": [{"fase": "contract", "sello_error": None}]},
    ]
    md = H.resumen(rows, "haiku", "hoy")
    assert "| DA0001 | apps | solve | 2 (2) |  |" in md
    assert "| DA0002 | apps | f | 1 (2) | timeout: the solver did not answer |" in md
    assert "| DD0003 | dafnybench | g | ✗ (1) |  |" in md
    assert "| **probadas (nivel 2)** | **1/2 (50 %)** | **0/1 (0 %)** | **1/3 (33 %)** |" in md
    assert "| aceptadas (nivel 1) | 2/2 (100 %) | 0/1 (0 %) | 2/3 (67 %) |" in md
    assert "- `unproven`: 3" in md and "- `E400`: 1" in md and "- `contract`: 1" in md
    assert "- timeout: 1" in md
