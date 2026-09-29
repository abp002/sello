#!/usr/bin/env python3
"""Contratos a ciegas: el modelo escribe el contrato desde el enunciado, sin resolver el problema.

Paso dos de 'El contrato escrito por otro caza lo que haiku deja pasar'. Diseño, reglas y
prerregistración en el vault: 'El contrato se puede escribir sin el cuerpo', con la enmienda
del 2026-09-29. El modelo recibe la spec, el enunciado y los dos ejemplos visibles, lo mismo que
quien escribe un programa entero, y escribe solo la principal con `{ sorry }` por cuerpo, más
los helpers que sus cláusulas llamen, completos. Su juez débil, hasta tres intentos:

  body      la principal trae cuerpo: solo se le pide el contrato;
  compile   el compilador (`check`) sobre todo el programa; con el hueco, los ejemplos de la
            principal quedan pendientes;
  examples  los dos ejemplos visibles por la prueba de literales (`literales.py`): con la
            respuesta visible por cuerpo, la principal tiene que cumplir su propio contrato.

Sale una corrida más (`contratos-<fecha>-<modelo>.jsonl`) que `harness3 --contratos` carga como
carga una del juez: el contrato de cada problema es el último programa del bucle, aceptado o no,
si compila (regla 1).

    uv run python bench/contratar.py --only clamp     # humo (regla 5)
    uv run python bench/contratar.py
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import RESULTADOS, SPEC, ask, extract, sello_lit  # noqa: E402
from harness3 import PROBLEMAS, ejemplos, llamada  # noqa: E402
import contrato as ct  # noqa: E402
import literales as lit  # noqa: E402

from sello.compile import check_source  # noqa: E402
from sello.errors import SelloError  # noqa: E402
from sello.nodes import Hole  # noqa: E402
from sello.parser import parse  # noqa: E402
from sello.pretty import unparse_fn  # noqa: E402

COND = "contrato"


def prompt(p: dict, prev: tuple[str, str] | None) -> str:
    head = (f"Below is the complete specification of Sello, a small programming language.\n\n"
            f"{SPEC}\n\n---\n\n"
            f"Task: write the contract of `{p['sello']}`, not its implementation. {p['statement']} "
            f"{ejemplos(p, 'sello')}\n"
            f"Write `{p['fn']}` with its signature and its `requires`, `ensures`, `effects` and "
            f"`example` lines, and `{{ sorry }}` as its body: someone else will write the body later, "
            f"against your contract. Any helper function your clauses call must be complete, with "
            f"its own contract and body. Do not write the body of `{p['fn']}`.\n"
            f"Reply with one ```sello block containing the whole program.")
    if prev is None:
        return head
    code, err = prev
    return (f"{head}\n\nYour previous program:\n```sello\n{code}\n```\n\nIt was rejected:\n"
            f"```\n{err}\n```\n\nFix it and reply with the whole corrected program in one ```sello block.")


def _error(e: SelloError) -> str:
    return json.dumps({"ok": False, "error": e.to_dict()}, ensure_ascii=False)


def juez_debil(code: str, p: dict) -> tuple[bool, str, str]:
    """(aceptado, feedback, fase): body | compile | examples | ok."""
    try:
        prog = parse(code)
    except SelloError as e:
        return False, _error(e), "compile"
    main = next((f for f in prog.fns if f.name == p["fn"]), None)
    if main is None:
        return False, f"`{p['fn']}` is missing: write it with its contract and `{{ sorry }}` as its body.", "compile"
    if not main.hole:
        return False, f"Write only the contract of `{p['fn']}`: its body must be `{{ sorry }}`.", "body"
    try:
        check_source(code)
    except SelloError as e:
        return False, _error(e), "compile"
    c = ct.extraer(code, p["fn"])
    rechazos = []
    for x in p["visible"]:
        v = lit.veredicto(c, p, x["args"], x["expect"])
        if v.que != lit.ADMITE:
            rechazos.append({"call": llamada(p, x["args"]), "correct_result": sello_lit(x["expect"]), "error": v.error})
    if not rechazos:
        return True, "", "ok"
    return False, json.dumps({"ok": False, "rejected": rechazos,
                              "note": f"Each call returned the correct result from the task, and the contract of "
                                      f"`{p['fn']}` rejected it."}, ensure_ascii=False), "examples"


def compila(code: str, fn: str) -> bool:
    """¿Se sostiene el contrato? El programa, con `{ sorry }` en la principal aunque el modelo le
    pusiera cuerpo, pasa `check`. Lo que no, cuenta como sin contrato (regla 1)."""
    try:
        prog = parse(code)
        if fn not in {f.name for f in prog.fns}:
            return False
        fns = [replace(f, body=Hole()) if f.name == fn else f for f in prog.fns]
        check_source("\n\n".join(unparse_fn(f) for f in fns))
    except SelloError:
        return False
    return True


def run_one(p: dict, model: str, max_attempts: int) -> dict:
    prev: tuple[str, str] | None = None
    attempts: list[dict] = []
    accepted_at: int | None = None
    code = ""
    for i in range(1, max_attempts + 1):
        a = ask(prompt(p, prev), model)
        code = extract(a["text"], "sello")
        ok, feedback, phase = juez_debil(code, p)
        m = re.search(r'"code":\s*"(E\d{3})"', feedback) if not ok else None
        attempts.append({"n": i, "ok": ok, "phase": phase, "sello_error": m.group(1) if m else None,
                         "cost": a["cost"], "tokens_in": a["tokens_in"], "tokens_out": a["tokens_out"],
                         "thinking": a.get("thinking", 0), "ms": a["ms"], "models": a.get("models"),
                         "code": code, "feedback": feedback[:2000]})
        print(f"  {p['fn']:<15} intento {i}: {'aceptado' if ok else phase + (' ' + m.group(1) if m else '')}",
              file=sys.stderr, flush=True)
        if ok:
            accepted_at = i
            break
        prev = (code, feedback)
    return {"problem": p["fn"], "cond": COND, "model": model, "accepted_at": accepted_at,
            "compila": compila(code, p["fn"]), "escribio_cuerpo": any(x["phase"] == "body" for x in attempts),
            "attempts": len(attempts), "cost": sum(x["cost"] for x in attempts),
            "tokens_in": sum(x["tokens_in"] for x in attempts),
            "tokens_out": sum(x["tokens_out"] for x in attempts),
            "thinking": sum(x["thinking"] for x in attempts),
            "ms": sum(x["ms"] for x in attempts), "code": code, "detail": attempts}


def resumen(rows: list[dict], model: str, when: str) -> str:
    out = [f"# Contratos a ciegas {when} · modelo `{model}`", "",
           "Prerregistrado en el vault: 'El contrato se puede escribir sin el cuerpo'.", "",
           "| Problema | aceptado en | compila | escribió cuerpo | fases de rechazo |", "|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: r["problem"]):
        fases = ", ".join(f"{x['phase']}{' ' + x['sello_error'] if x['sello_error'] else ''}"
                          for x in r["detail"] if not x["ok"]) or "-"
        out.append(f"| {r['problem']} | {r['accepted_at'] or '-'} | {'sí' if r['compila'] else 'no'} | "
                   f"{'sí' if r['escribio_cuerpo'] else 'no'} | {fases} |")
    acc = [r for r in rows if r["accepted_at"]]
    out += ["", f"- Aceptados al primer intento: {sum(r['accepted_at'] == 1 for r in rows)}/{len(rows)}; "
                f"al final: {len(acc)}/{len(rows)}; compilan: {sum(r['compila'] for r in rows)}/{len(rows)}.",
            f"- Intentos medios (todos): {sum(r['attempts'] for r in rows) / max(1, len(rows)):.2f}; "
            f"hasta aceptar: {sum(r['accepted_at'] for r in acc) / max(1, len(acc)):.2f}.",
            f"- Escribió cuerpo en la principal (regla 5): {sum(r['escribio_cuerpo'] for r in rows)}/{len(rows)}.",
            f"- Tokens de salida: {sum(r['tokens_out'] for r in rows)} (razonamiento {sum(r['thinking'] for r in rows)}); "
            f"coste USD {sum(r['cost'] for r in rows):.3f}; tiempo {sum(r['ms'] for r in rows) / 1000:.0f} s.",
            f"- Modelos: {', '.join(sorted({m for r in rows for x in r['detail'] for m in (x.get('models') or [])}))}."]
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--only", help="nombre de un problema")
    ap.add_argument("--attempts", type=int, default=3)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    probs = [json.loads(f.read_text()) for f in sorted(PROBLEMAS.glob("*.json"))]
    if args.only:
        probs = [p for p in probs if p["fn"] == args.only]
    when = dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    print(f"{len(probs)} problemas, modelo {args.model}, hasta {args.attempts} intentos", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        rows = list(ex.map(lambda p: run_one(p, args.model, args.attempts), probs))
    RESULTADOS.mkdir(exist_ok=True)
    tag = f"contratos-{when}-{args.model}"
    base = RESULTADOS / (tag if not args.only else f"humo-{tag}")
    base.with_suffix(".jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    md = resumen(rows, args.model, when)
    base.with_suffix(".md").write_text(md)
    print(md)
    print(f"detalle: {base.with_suffix('.jsonl')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
