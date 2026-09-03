#!/usr/bin/env python3
"""Tercera medición: el juez imperfecto. Cuánto error llega a producción.

El bucle de generación solo ve el juez débil: compilador + los dos ejemplos visibles del
enunciado. Cuando acepta, la solución pasa al oráculo (referencia + casos generados,
`bench/ambiguos/`), que cuenta silenciosos, rechazados y cazados por zona. Diseño y
prerregistración en el vault: 'El juez imperfecto mide lo que llega a producción'.

Condiciones: sello · python · python_asserts (Python con la instrucción de poner asserts).

    uv run python bench/harness3.py --model haiku
    uv run python bench/harness3.py --model haiku --only nth --cond sello   # humo
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import RESULTADOS, ROOT, SPEC, ask, extract, py_val, sello_lit  # noqa: E402
import juez  # noqa: E402

AQUI = Path(__file__).resolve().parent
PROBLEMAS = AQUI / "ambiguos"
CONDS = ["sello", "python", "python_asserts"]


# ---------- prompts ----------

def llamada(p: dict, args: list) -> str:
    return f"{p['fn']}(" + ", ".join(sello_lit(a) for a in args) + ")"


def ejemplos(p: dict, lang: str) -> str:
    out = []
    for c in p["visible"]:
        if lang == "sello":
            out.append(f"{llamada(p, c['args'])} == {sello_lit(c['expect'])}")
        else:
            args = ", ".join(repr(py_val(a)) for a in c["args"])
            out.append(f"{p['fn']}({args}) == {py_val(c['expect'])!r}")
    return "For example: " + "; ".join(out) + "."


def prompt(p: dict, cond: str, prev: tuple[str, str] | None) -> str:
    if cond == "sello":
        head = (f"Below is the complete specification of Sello, a small programming language.\n\n"
                f"{SPEC}\n\n---\n\n"
                f"Task: write a Sello program that defines `{p['sello']}`. {p['statement']} "
                f"{ejemplos(p, 'sello')}\n"
                f"You may add helper functions. Every function needs its contract clauses. "
                f"Tests will call `{p['fn']}`.\n"
                f"Reply with one ```sello block containing the whole program.")
        fence, tail = "sello", "the whole corrected program"
    else:
        extra = ""
        if cond == "python_asserts":
            extra = ("Use `assert` to check every precondition on the arguments at the start of "
                     "the function, and `assert` every property the result must satisfy before "
                     "returning it. ")
        head = (f"Task: write a Python function `{p['python']}`. {p['statement']} "
                f"{ejemplos(p, 'python')}\n"
                f"{extra}No imports, no input/output, no prints. You may add helper functions. "
                f"Tests will call `{p['fn']}`.\n"
                f"Reply with one ```python block containing the whole code.")
        fence, tail = "python", "the whole corrected code"
    if prev is None:
        return head
    code, err = prev
    return (f"{head}\n\nYour previous code:\n```{fence}\n{code}\n```\n\nIt was rejected:\n"
            f"```\n{err}\n```\n\nFix it and reply with {tail} in one ```{fence} block.")


# ---------- ejecución caso a caso ----------

def casos_sello(p: dict, casos: list[dict]) -> str:
    return json.dumps([{"call": llamada(p, c["args"]), "expect": sello_lit(c["expect"])} for c in casos])


def ejecutar_sello(code: str, p: dict, casos: list[dict], timeout: int = 60) -> list[dict] | dict:
    """Corre `sello test`. Devuelve la lista de casos con `result` bruto, o el error de compilación."""
    with tempfile.TemporaryDirectory() as d:
        src = Path(d, "sol.sello"); src.write_text(code + "\n")
        cj = Path(d, "cases.json"); cj.write_text(casos_sello(p, casos))
        try:
            r = subprocess.run([sys.executable, "-m", "sello.cli", "test", str(src), str(cj)],
                               capture_output=True, text=True, timeout=timeout, cwd=ROOT)
        except subprocess.TimeoutExpired:
            return {"error": {"code": "E500", "what": f"timeout after {timeout}s"}, "timeout": True}
    out = r.stdout.strip() or r.stderr.strip()[-1500:]
    try:
        d = json.loads(out)
    except json.JSONDecodeError:
        return {"error": {"code": "E000", "what": out[-800:]}}
    if "error" in d:
        return d
    fallos = {f["call"]: f for f in d.get("failed", [])}
    return [{**c, "call": llamada(p, c["args"]), "result": juez.resultado_sello(fallos.get(llamada(p, c["args"]))),
             "detail": fallos.get(llamada(p, c["args"]))} for c in casos]


DRIVER = r'''
import json, signal, sys, traceback
code, cases, fn = sys.argv[1], json.loads(sys.argv[2]), sys.argv[3]
ns = {}
try:
    exec(open(code).read(), ns)
    f = ns[fn]
except Exception:
    print(json.dumps({"error": traceback.format_exc(limit=2)[-1200:]})); sys.exit(1)
class Timeout(Exception): pass
def alarm(*_): raise Timeout()
signal.signal(signal.SIGALRM, alarm)
out = []
for c in cases:
    signal.alarm(3)
    try:
        got = f(*c["args"])
        exp = c["expect"]
        ok = got == exp and isinstance(got, bool) == isinstance(exp, bool)
        out.append({"status": "ok" if ok else "wrong", "got": repr(got)})
    except AssertionError as e:
        out.append({"status": "assert", "got": f"AssertionError: {e}"})
    except Timeout:
        out.append({"status": "timeout", "got": "timeout"})
    except BaseException as e:
        out.append({"status": "raise", "got": f"{type(e).__name__}: {e}"[:200]})
    finally:
        signal.alarm(0)
print(json.dumps(out))
'''


def ejecutar_python(code: str, p: dict, casos: list[dict], timeout: int = 60) -> list[dict] | dict:
    with tempfile.TemporaryDirectory() as d:
        src = Path(d, "sol.py"); src.write_text(code + "\n")
        drv = Path(d, "driver.py"); drv.write_text(DRIVER)
        cj = json.dumps([{"args": [py_val(a) for a in c["args"]], "expect": py_val(c["expect"])} for c in casos])
        try:
            r = subprocess.run([sys.executable, str(drv), str(src), cj, p["fn"]],
                               capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"error": f"timeout after {timeout}s"}
    try:
        d = json.loads(r.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return {"error": (r.stdout + r.stderr)[-1200:]}
    if isinstance(d, dict):
        return d
    return [{**c, "call": llamada(p, c["args"]), "result": juez.resultado_python(x["status"]), "detail": x}
            for c, x in zip(casos, d)]


def ejecutar(cond: str, code: str, p: dict, casos: list[dict], timeout: int = 60) -> list[dict] | dict:
    return (ejecutar_sello if cond == "sello" else ejecutar_python)(code, p, casos, timeout)


# ---------- juez débil ----------

def juez_debil(cond: str, code: str, p: dict) -> tuple[bool, str, str]:
    """(aceptado, feedback, fase). Compila y pasa los ejemplos visibles."""
    r = ejecutar(cond, code, p, p["visible"])
    if isinstance(r, dict):
        return False, json.dumps(r, ensure_ascii=False), "compile"
    fallos = [x for x in r if x["result"] != juez.OK]
    if not fallos:
        return True, "", "ok"
    if cond == "sello":
        fb = json.dumps({"ok": False, "failed": [x["detail"] for x in fallos]}, ensure_ascii=False)
    else:
        fb = "\n".join(f"{x['call']}: expected {py_val(x['expect'])!r}, got {x['detail']['got']}" for x in fallos)
    return False, fb, "tests"


# ---------- una corrida ----------

def run_one(p: dict, cond: str, model: str, max_attempts: int) -> dict:
    prev: tuple[str, str] | None = None
    attempts: list[dict] = []
    accepted_at: int | None = None
    code = ""
    for i in range(1, max_attempts + 1):
        a = ask(prompt(p, cond, prev), model)
        code = extract(a["text"], "sello" if cond == "sello" else "python")
        ok, feedback, phase = juez_debil(cond, code, p)
        m = re.search(r'"code":\s*"(E\d{3})"', feedback) if (cond == "sello" and not ok) else None
        attempts.append({"n": i, "ok": ok, "phase": phase, "sello_error": m.group(1) if m else None,
                         "cost": a["cost"], "tokens_in": a["tokens_in"], "tokens_out": a["tokens_out"],
                         "thinking": a.get("thinking", 0), "ms": a["ms"], "code": code, "feedback": feedback[:2000]})
        print(f"  {p['fn']:<15} {cond:<15} intento {i}: {'aceptado' if ok else phase + (' ' + m.group(1) if m else '')}",
              file=sys.stderr, flush=True)
        if ok:
            accepted_at = i
            break
        prev = (code, feedback)

    oracle_cases: list[dict] = []
    oracle: dict = {}
    if accepted_at:
        r = ejecutar(cond, code, p, p["oracle"])
        if isinstance(r, dict):
            oracle_cases = [{**c, "result": juez.REJECT, "detail": r} for c in p["oracle"]]
        else:
            oracle_cases = r
        oracle = juez.contar(oracle_cases)
        print(f"  {p['fn']:<15} {cond:<15} oráculo: silenciosos {oracle['silenciosos']} "
              f"(dom {oracle['dom_silencioso']}, amb {oracle['amb_silencioso']}) · ruidosos dom {oracle['dom_ruidoso']} "
              f"· declarados amb {oracle['amb_declarado']} · cazados {oracle['cazados']}", file=sys.stderr, flush=True)

    return {"problem": p["fn"], "cond": cond, "model": model, "accepted_at": accepted_at,
            "attempts": len(attempts), "cost": sum(x["cost"] for x in attempts),
            "tokens_in": sum(x["tokens_in"] for x in attempts),
            "tokens_out": sum(x["tokens_out"] for x in attempts),
            "thinking": sum(x["thinking"] for x in attempts),
            "ms": sum(x["ms"] for x in attempts), "code": code if accepted_at else None,
            "oracle": oracle, "oracle_cases": [{k: v for k, v in c.items() if k != "expect"} | {"expect": c["expect"]}
                                              for c in oracle_cases],
            "detail": attempts}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--cond", choices=CONDS + ["all"], default="all")
    ap.add_argument("--only", help="nombre de un problema")
    ap.add_argument("--attempts", type=int, default=5)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    probs = [json.loads(f.read_text()) for f in sorted(PROBLEMAS.glob("*.json"))]
    if args.only:
        probs = [p for p in probs if p["fn"] == args.only]
    conds = CONDS if args.cond == "all" else [args.cond]
    jobs = [(p, c) for p in probs for c in conds]
    when = dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    print(f"{len(jobs)} corridas, modelo {args.model}, hasta {args.attempts} intentos", file=sys.stderr)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        rows = list(ex.map(lambda j: run_one(j[0], j[1], args.model, args.attempts), jobs))

    RESULTADOS.mkdir(exist_ok=True)
    tag = f"juez-{when}-{args.model}"
    base = RESULTADOS / (tag if not args.only else f"humo-{tag}")
    with open(base.with_suffix(".jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    md = juez.resumen(rows, args.model, when)
    base.with_suffix(".md").write_text(md)
    print(md)
    print(f"detalle: {base.with_suffix('.jsonl')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
