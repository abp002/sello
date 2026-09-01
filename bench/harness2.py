#!/usr/bin/env python3
"""Segunda medición: el modelo escribe funciones nuevas sobre una librería ya certificada.

Dos condiciones con la misma tarea y el mismo modelo:
  file  el prompt lleva el fuente entero de la librería (lo que haría un fichero)
  api   el prompt lleva solo la salida de `sello sig` de cada función: firma, contrato,
        certificado. Sin cuerpos. Es "la sintaxis de lectura es una API".

Si `api` no baja los aciertos y sí baja los tokens, la decisión central se sostiene.

    uv run python bench/harness2.py --model sonnet
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import RESULTADOS, SPEC, ask, check_sello, extract, resumen  # noqa: E402

AQUI = Path(__file__).resolve().parent
LIB = (AQUI / "problemas2" / "libreria.sello").read_text()


def sigs_json() -> str:
    from sello.store import Store
    with tempfile.TemporaryDirectory() as d:
        st = Store(Path(d, "s.db"))
        st.add(LIB)
        out = []
        for n in st.names():
            s = st.sig(n["name"])
            c = s["certificate"]
            out.append({"signature": s["signature"], "requires": s["requires"], "ensures": s["ensures"],
                        "certificate": f"level {c['level']}, ok, {c['examples']} examples"})
    return json.dumps(out, indent=1)


SIGS = sigs_json()


def prompt(p: dict, context: str, prev: tuple[str, str] | None) -> str:
    head = (f"Below is the complete specification of Sello, a small programming language.\n\n{SPEC}\n\n---\n\n")
    if context == "file":
        head += (f"This Sello file already exists and your code will be appended to it. "
                 f"Do not redefine these functions:\n```sello\n{LIB}\n```\n\n")
    else:
        head += (f"The store already contains these certified functions. You can call them. "
                 f"You cannot see their bodies and must not redefine them:\n```json\n{SIGS}\n```\n\n")
    head += (f"Task: write `{p['sello']}`. {p['statement']}\n"
             f"Use the existing functions where they help. You may add helper functions. "
             f"Hidden tests will call `{p['fn']}`.\n"
             f"Reply with one ```sello block containing only the new code.")
    if prev is None:
        return head
    code, err = prev
    return (f"{head}\n\nYour previous code:\n```sello\n{code}\n```\n\nThe compiler rejected it:\n"
            f"```json\n{err}\n```\n\nFix it and reply with the corrected new code in one ```sello block.")


def run_one(p: dict, context: str, model: str, max_attempts: int) -> dict:
    prev = None
    attempts: list[dict] = []
    solved_at = None
    for i in range(1, max_attempts + 1):
        a = ask(prompt(p, context, prev), model)
        code = extract(a["text"], "sello")
        ok, feedback, phase = check_sello(LIB + "\n\n" + code, p)
        m = re.search(r'"code":\s*"(E\d{3})"', feedback) if not ok else None
        attempts.append({"n": i, "ok": ok, "phase": phase, "sello_error": m.group(1) if m else None,
                         "cost": a["cost"], "tokens_in": a["tokens_in"], "tokens_out": a["tokens_out"],
                         "ms": a["ms"], "code": code, "feedback": feedback[:2000]})
        print(f"  {p['fn']:<14} {context:<5} intento {i}: {'OK' if ok else phase + (' ' + m.group(1) if m else '')}",
              file=sys.stderr, flush=True)
        if ok:
            solved_at = i
            break
        prev = (code, feedback)
    return {"problem": p["fn"], "lang": context, "model": model, "solved_at": solved_at,
            "attempts": len(attempts), "cost": sum(x["cost"] for x in attempts),
            "tokens_in": sum(x["tokens_in"] for x in attempts), "tokens_out": sum(x["tokens_out"] for x in attempts),
            "ms": sum(x["ms"] for x in attempts), "detail": attempts}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--context", choices=["file", "api", "both"], default="both")
    ap.add_argument("--only")
    ap.add_argument("--attempts", type=int, default=5)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    probs = [json.loads(f.read_text()) for f in sorted((AQUI / "problemas2").glob("*.json"))]
    if args.only:
        probs = [p for p in probs if p["fn"] == args.only]
    ctxs = ["file", "api"] if args.context == "both" else [args.context]
    jobs = [(p, c) for p in probs for c in ctxs]
    when = dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    print(f"{len(jobs)} corridas (librería: {len(LIB)} chars, sigs: {len(SIGS)} chars), modelo {args.model}", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        rows = list(ex.map(lambda j: run_one(j[0], j[1], args.model, args.attempts), jobs))
    RESULTADOS.mkdir(exist_ok=True)
    base = RESULTADOS / f"{when}-{args.model}-libreria"
    with open(base.with_suffix(".jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    md = resumen(rows, args.model, when).replace("# Medición", "# Medición sobre librería (file vs api)")
    base.with_suffix(".md").write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
