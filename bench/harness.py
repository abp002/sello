#!/usr/bin/env python3
"""El experimento: intentos que necesita un modelo hasta que su programa compila y pasa
los casos ocultos, en Sello y en Python, con la misma spec y los mismos problemas.

    uv run python bench/harness.py --model sonnet            # todo
    uv run python bench/harness.py --only max_of --lang sello  # humo

Llama al modelo con `claude -p` en modo limpio (sin herramientas, sin settings, sin MCP):
unos 300 tokens de sobrecarga por llamada. Cada intento es una llamada nueva que recibe
el programa anterior y el error, no una sesión.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parent
SPEC = (ROOT / "spec" / "SPEC.md").read_text()
PROBLEMAS = AQUI / "problemas"
RESULTADOS = AQUI / "resultados"

SYSTEM = ("You are a code generator. Reply with exactly one fenced code block and nothing "
          "else: no prose before or after. Do not use tools.")


# ---------- literales ----------

def sello_lit(v: object) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        return json.dumps(v)
    if isinstance(v, list):
        return "[" + ", ".join(sello_lit(x) for x in v) + "]"
    if v is None:
        return "None"
    if isinstance(v, dict) and "some" in v:
        return f"Some({sello_lit(v['some'])})"
    raise TypeError(v)


def py_val(v: object) -> object:
    """JSON neutro -> valor Python (Option se aplana a valor-o-None)."""
    if isinstance(v, dict) and "some" in v:
        return py_val(v["some"])
    if isinstance(v, list):
        return [py_val(x) for x in v]
    return v


# ---------- prompts ----------

def prompt_sello(p: dict, prev: tuple[str, str] | None) -> str:
    head = (f"Below is the complete specification of Sello, a small programming language.\n\n"
            f"{SPEC}\n\n---\n\n"
            f"Task: write a Sello program that defines `{p['sello']}`. {p['statement']}\n"
            f"You may add helper functions. Every function needs its contract clauses. "
            f"Hidden tests will call `{p['fn']}`.\n"
            f"Reply with one ```sello block containing the whole program.")
    if prev is None:
        return head
    code, err = prev
    return (f"{head}\n\nYour previous program:\n```sello\n{code}\n```\n\n"
            f"The compiler rejected it:\n```json\n{err}\n```\n\n"
            f"Fix it and reply with the whole corrected program in one ```sello block.")


def prompt_python(p: dict, prev: tuple[str, str] | None) -> str:
    head = (f"Task: write a Python function `{p['python']}`. {p['statement']}\n"
            f"No imports, no input/output, no prints. You may add helper functions. "
            f"Hidden tests will call `{p['fn']}`.\n"
            f"Reply with one ```python block containing the whole code.")
    if prev is None:
        return head
    code, err = prev
    return (f"{head}\n\nYour previous code:\n```python\n{code}\n```\n\n"
            f"It failed:\n```\n{err}\n```\n\n"
            f"Fix it and reply with the whole corrected code in one ```python block.")


# ---------- modelo ----------

def ask(prompt: str, model: str) -> dict:
    cmd = ["claude", "-p", prompt, "--model", model, "--tools", "", "--system-prompt", SYSTEM,
           "--setting-sources", "", "--strict-mcp-config", "--disable-slash-commands",
           "--no-chrome", "--no-session-persistence", "--output-format", "json"]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600, cwd=tempfile.gettempdir())
    ms = int((time.time() - t0) * 1000)
    try:
        d = json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"text": "", "cost": 0.0, "tokens_in": 0, "tokens_out": 0, "ms": ms,
                "error": (r.stdout + r.stderr)[-500:]}
    u = d.get("usage", {})
    return {"text": d.get("result", ""), "cost": d.get("total_cost_usd", 0.0),
            "tokens_in": u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
            + u.get("cache_read_input_tokens", 0),
            "tokens_out": u.get("output_tokens", 0), "ms": ms}


def extract(text: str, lang: str) -> str:
    m = re.search(rf"```{lang}\s*\n(.*?)```", text, re.S) or re.search(r"```\w*\s*\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()


# ---------- verificación ----------

def check_sello(code: str, p: dict) -> tuple[bool, str, str]:
    """(ok, feedback, fase). Fase: compile | tests | ok."""
    with tempfile.TemporaryDirectory() as d:
        src = Path(d, "sol.sello"); src.write_text(code + "\n")
        cases = Path(d, "cases.json")
        cases.write_text(json.dumps([
            {"call": f"{p['fn']}(" + ", ".join(sello_lit(a) for a in c["args"]) + ")",
             "expect": sello_lit(c["expect"])} for c in p["cases"]]))
        try:
            r = subprocess.run([sys.executable, "-m", "sello.cli", "test", str(src), str(cases)],
                               capture_output=True, text=True, timeout=60, cwd=ROOT)
        except subprocess.TimeoutExpired:
            return False, json.dumps({"ok": False, "error": {"code": "E500", "what": "Runtime error: timeout after 60s"}}), "tests"
    out = r.stdout.strip() or r.stderr.strip()[-1500:]
    try:
        d = json.loads(out)
    except json.JSONDecodeError:
        return False, out, "compile"
    if d.get("ok"):
        return True, out, "ok"
    return False, out, ("compile" if "error" in d else "tests")


DRIVER = r'''
import json, sys, traceback
code, cases, fn = sys.argv[1], json.loads(sys.argv[2]), sys.argv[3]
ns = {}
try:
    exec(open(code).read(), ns)
    f = ns[fn]
except Exception:
    print(json.dumps({"ok": False, "phase": "compile", "error": traceback.format_exc(limit=2)[-1200:]})); sys.exit(1)
failed = []
for c in cases:
    call = fn + "(" + ", ".join(repr(a) for a in c["args"]) + ")"
    try:
        got = f(*c["args"])
        exp = c["expect"]
        if got != exp or isinstance(got, bool) != isinstance(exp, bool):
            failed.append(f"{call}: expected {exp!r}, got {got!r}")
    except Exception as e:
        failed.append(f"{call}: raised {type(e).__name__}: {e}")
print(json.dumps({"ok": not failed, "phase": "ok" if not failed else "tests", "error": "\n".join(failed)}))
sys.exit(0 if not failed else 1)
'''


def check_python(code: str, p: dict) -> tuple[bool, str, str]:
    with tempfile.TemporaryDirectory() as d:
        src = Path(d, "sol.py"); src.write_text(code + "\n")
        drv = Path(d, "driver.py"); drv.write_text(DRIVER)
        cases = json.dumps([{"args": [py_val(a) for a in c["args"]], "expect": py_val(c["expect"])}
                            for c in p["cases"]])
        try:
            r = subprocess.run([sys.executable, str(drv), str(src), cases, p["fn"]],
                               capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired:
            return False, "timeout after 30s (infinite loop or recursion?)", "tests"
    try:
        d = json.loads(r.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return False, (r.stdout + r.stderr)[-1200:], "compile"
    return bool(d["ok"]), d["error"], d["phase"]


# ---------- una corrida ----------

def run_one(p: dict, lang: str, model: str, max_attempts: int) -> dict:
    prev: tuple[str, str] | None = None
    attempts: list[dict] = []
    solved_at: int | None = None
    for i in range(1, max_attempts + 1):
        prompt = prompt_sello(p, prev) if lang == "sello" else prompt_python(p, prev)
        a = ask(prompt, model)
        code = extract(a["text"], lang)
        ok, feedback, phase = (check_sello if lang == "sello" else check_python)(code, p)
        err_code = None
        if lang == "sello" and not ok:
            m = re.search(r'"code":\s*"(E\d{3})"', feedback)
            err_code = m.group(1) if m else None
        attempts.append({"n": i, "ok": ok, "phase": phase, "sello_error": err_code,
                         "cost": a["cost"], "tokens_in": a["tokens_in"], "tokens_out": a["tokens_out"],
                         "ms": a["ms"], "code": code, "feedback": feedback[:2000]})
        print(f"  {p['fn']:<13} {lang:<6} intento {i}: {'OK' if ok else phase + (' ' + err_code if err_code else '')}",
              file=sys.stderr, flush=True)
        if ok:
            solved_at = i
            break
        prev = (code, feedback)
    return {"problem": p["fn"], "lang": lang, "model": model, "solved_at": solved_at,
            "attempts": len(attempts), "cost": sum(x["cost"] for x in attempts),
            "tokens_in": sum(x["tokens_in"] for x in attempts),
            "tokens_out": sum(x["tokens_out"] for x in attempts),
            "ms": sum(x["ms"] for x in attempts), "detail": attempts}


# ---------- resumen ----------

def resumen(rows: list[dict], model: str, when: str) -> str:
    langs = sorted({r["lang"] for r in rows})
    probs = sorted({r["problem"] for r in rows})
    by = {(r["problem"], r["lang"]): r for r in rows}
    out = [f"# Medición {when} · modelo `{model}`", "",
           "Intentos hasta compilar y pasar los casos ocultos (`-` = no resuelto).", "",
           "| Problema | " + " | ".join(langs) + " |", "|---|" + "---|" * len(langs)]
    for pr in probs:
        cells = []
        for l in langs:
            r = by.get((pr, l))
            cells.append("-" if r is None else (str(r["solved_at"]) if r["solved_at"] else f"✗ ({r['attempts']})"))
        out.append(f"| {pr} | " + " | ".join(cells) + " |")
    out += ["", "| | " + " | ".join(langs) + " |", "|---|" + "---|" * len(langs)]
    def stat(name, f):
        out.append(f"| {name} | " + " | ".join(f(l) for l in langs) + " |")
    def rs(l): return [r for r in rows if r["lang"] == l]
    def solved(l): return [r for r in rs(l) if r["solved_at"]]
    stat("resueltos", lambda l: f"{len(solved(l))}/{len(rs(l))}")
    stat("a la primera", lambda l: str(sum(1 for r in solved(l) if r['solved_at'] == 1)))
    stat("media de intentos (resueltos)", lambda l: f"{sum(r['solved_at'] for r in solved(l)) / max(1, len(solved(l))):.2f}")
    stat("tokens de salida", lambda l: str(sum(r['tokens_out'] for r in rs(l))))
    stat("tokens de entrada", lambda l: str(sum(r['tokens_in'] for r in rs(l))))
    stat("coste USD", lambda l: f"{sum(r['cost'] for r in rs(l)):.3f}")
    stat("tiempo total (s)", lambda l: f"{sum(r['ms'] for r in rs(l)) / 1000:.0f}")
    errs: dict[str, int] = {}
    for r in rs("sello") if "sello" in langs else []:
        for a in r["detail"]:
            if a["sello_error"]:
                errs[a["sello_error"]] = errs.get(a["sello_error"], 0) + 1
    if errs:
        out += ["", "Errores de Sello por código (todos los intentos):", ""]
        out += [f"- `{k}`: {v}" for k, v in sorted(errs.items(), key=lambda kv: -kv[1])]
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--lang", choices=["sello", "python", "both"], default="both")
    ap.add_argument("--only", help="nombre de un problema")
    ap.add_argument("--attempts", type=int, default=5)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    probs = [json.loads(f.read_text()) for f in sorted(PROBLEMAS.glob("*.json"))]
    if args.only:
        probs = [p for p in probs if p["fn"] == args.only]
    langs = ["sello", "python"] if args.lang == "both" else [args.lang]
    jobs = [(p, l) for p in probs for l in langs]
    when = dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    print(f"{len(jobs)} corridas, modelo {args.model}, hasta {args.attempts} intentos", file=sys.stderr)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        rows = list(ex.map(lambda j: run_one(j[0], j[1], args.model, args.attempts), jobs))

    RESULTADOS.mkdir(exist_ok=True)
    base = RESULTADOS / f"{when}-{args.model}" if not args.only else RESULTADOS / f"humo-{when}-{args.model}"
    with open(base.with_suffix(".jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    md = resumen(rows, args.model, when)
    base.with_suffix(".md").write_text(md)
    print(md)
    print(f"detalle: {base.with_suffix('.jsonl')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
