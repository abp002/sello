"""La medición del probador (bench/probador.py): la regla de recuento no miente."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench"))
import probador as pb  # noqa: E402


def test_motivo_agrupa_los_unknown():
    assert pb.motivo("undecided: `ensures ...`") == "undecided"
    assert pb.motivo("timeout: the solver did not answer") == "timeout"
    assert pb.motivo("termination: no argument decreases") == "termination"
    assert pb.motivo("mutual recursion: termination not checked") == "mutual recursion"
    assert pb.motivo("cualquier otra cosa") == "undecided"


def test_evaluar_distingue_bug_del_probador_de_fallo_de_la_herramienta():
    ok = {"ok": True, "functions": [{"name": "f", "level": 2}, {"name": "g", "level": 1, "unproven": "timeout"}]}
    r = pb.evaluar({"kind": "solucion", "problem": "f", "code": ""}, check=lambda code: ok)
    assert r["ok"] and r["principal"] == 2 and r["funciones"][1]["motivo"] == "timeout"
    bug = {"ok": False, "error": {"code": "E201", "what": "...", "found_by": "prover"}}
    r = pb.evaluar({"kind": "mutante", "problem": "f", "code": ""}, check=lambda code: bug)
    assert not r["ok"] and r["error"]["probador"] and r["principal"] is None
    tool = {"ok": False, "error": {"code": "E500", "what": "timeout"}}
    assert pb.evaluar({"kind": "mutante", "problem": "f", "code": ""}, check=lambda code: tool)["error"]["probador"] is False


def test_resumen_cuenta_matados_y_niveles():
    rows = [
        {"kind": "solucion", "problem": "f", "cond": "sello", "model": "haiku", "ok": True, "error": None, "ms": 10,
         "funciones": [{"name": "f", "level": 2, "motivo": None}, {"name": "g", "level": 1, "motivo": "undecided"}], "principal": 2},
        {"kind": "mutante", "problem": "f", "cond": "sello", "model": "haiku", "cat": "cazado", "ok": False, "ms": 5,
         "error": {"code": "E201", "what": "", "probador": True}},
        {"kind": "mutante", "problem": "f", "cond": "sello", "model": "haiku", "cat": "silencioso", "ok": True, "ms": 5,
         "error": None, "funciones": [], "principal": 2},
        {"kind": "mutante", "problem": "f", "cond": "sello", "model": "haiku", "cat": "equivalente", "ok": False, "ms": 5,
         "error": {"code": "E300", "what": "", "probador": True}},
    ]
    md = pb.resumen(rows, "hoy")
    assert "| f | 2 · 1/2 |" in md
    assert "| **matados por el probador / llegaban** | **1/2 (50 %)** |" in md
    assert "| equivalentes en el dominio matados (bug fuera del oráculo) | 1/1 (100 %) |" in md
    assert "| · matados con E300 | 1 |" in md
