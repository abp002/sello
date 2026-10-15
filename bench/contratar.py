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

Para el experimento decisivo (SEL-9), dos variantes:

  --lang python  el mismo encargo en Python (`contrato_py.py`): la principal con su docstring de
                 `pre:`/`post:` y `...` por cuerpo; su juez débil es igual (cuerpo, compila, los
                 ejemplos visibles con la respuesta visible por cuerpo, ejecutados con contratos).
  --aviso        (SEL-14; en Python, issue #3 con CrossHair) si el contrato aceptado admite dos respuestas para una entrada
                 (`sello.unique`), una sola vuelta más con el testigo. No es un rechazo: lo que el
                 modelo devuelva tras el aviso vale si compila y admite los ejemplos.
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import RESULTADOS, SPEC, ask, extract, py_val, sello_lit  # noqa: E402
from harness3 import PROBLEMAS, ejemplos, llamada  # noqa: E402
import contrato as ct  # noqa: E402
import literales as lit  # noqa: E402

import contrato_py as cp  # noqa: E402
from harness3 import ejecutar_python  # noqa: E402

from sello.compile import check_source, compile_source  # noqa: E402
from sello.errors import SelloError  # noqa: E402
from sello.nodes import Hole  # noqa: E402
from sello.parser import parse  # noqa: E402
from sello.pretty import unparse_fn  # noqa: E402
from sello.unique import AMBIGUOUS, unique_program  # noqa: E402

COND = "contrato"
COND_PY = "contrato_py"


def prompt_py(p: dict, prev: tuple[str, str] | None) -> str:
    """El encargo de `prompt` en Python, con las mismas reglas de contrato que la spec de Sello."""
    head = (f"Task: write the contract of the Python function `{p['python']}`, not its implementation. "
            f"{p['statement']} {ejemplos(p, 'python')}\n"
            f"Write `{p['fn']}` with its signature and a docstring that holds its contract in the format "
            f"CrossHair reads: one line `pre: <boolean expression on the arguments>` per precondition and "
            f"one line `post: <boolean expression>` per postcondition, where `__return__` is the returned "
            f"value. Its body must be just `...`: someone else will write the body later, against your "
            f"contract. The conditions are checked on every call, and a tool searches for inputs that "
            f"break them. Preconditions state everything the task lets you assume about the arguments "
            f"(a value is unique, the list has no repeats, `k` is within bounds); whatever is not in them "
            f"the body must handle. Postconditions must reject wrong results: a condition that every "
            f"return value satisfies certifies nothing, and a bound alone (`__return__ >= 1`, "
            f"`__return__ <= len(xs)`) does not reject a wrong value inside the bound. State what the "
            f"result contains or how it relates to the arguments. Any helper function your conditions "
            f"call must be complete. No imports.\n"
            f"Reply with one ```python block containing the whole code.")
    if prev is None:
        return head
    code, err = prev
    return (f"{head}\n\nYour previous code:\n```python\n{code}\n```\n\nIt was rejected:\n"
            f"```\n{err}\n```\n\nFix it and reply with the whole corrected code in one ```python block.")


def _solo_contrato(main: ast.FunctionDef) -> bool:
    """¿El cuerpo es solo `...` (tras el docstring)?"""
    body = main.body[1:] if ast.get_docstring(main, clean=False) is not None else main.body
    return len(body) == 1 and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
        and body[0].value.value is Ellipsis


def juez_debil_py(code: str, p: dict) -> tuple[bool, str, str]:
    """(aceptado, feedback, fase): body | compile | examples | ok, como `juez_debil`."""
    try:
        main = next((n for n in ast.parse(code).body if isinstance(n, ast.FunctionDef) and n.name == p["fn"]), None)
    except SyntaxError as e:
        return False, f"SyntaxError: {e}", "compile"
    if main is None:
        return False, f"`{p['fn']}` is missing: write it with its contract and `...` as its body.", "compile"
    if not _solo_contrato(main):
        return False, f"Write only the contract of `{p['fn']}`: its body must be `...`.", "body"
    if not cp.condiciones(ast.get_docstring(main))[1]:
        return False, f"`{p['fn']}` has no `post:` line in its docstring.", "compile"
    rechazos = []
    for x in p["visible"]:
        r = ejecutar_python(_con_literal(code, p, x["expect"]), p, [x], contratos=True)
        if isinstance(r, dict):
            return False, json.dumps(r, ensure_ascii=False), "compile"
        if r[0]["result"] != "ok":
            rechazos.append({"call": r[0]["call"], "correct_result": repr(py_val(x["expect"])),
                             "error": r[0]["detail"]["got"]})
    if not rechazos:
        return True, "", "ok"
    return False, json.dumps({"ok": False, "rejected": rechazos,
                              "note": f"Each call returned the correct result from the task, and the contract of "
                                      f"`{p['fn']}` rejected it."}, ensure_ascii=False), "examples"


def _con_literal(code: str, p: dict, expect: object) -> str:
    """El programa con la principal devolviendo esa respuesta: el contrato juzgado sin cuerpo."""
    tree = ast.parse(code)
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name == p["fn"]:
            doc = n.body[:1] if ast.get_docstring(n, clean=False) is not None else []
            n.body = doc + [ast.Return(ast.Constant(py_val(expect)))]
    return ast.unparse(tree)


def compila_py(code: str, fn: str) -> bool:
    """¿Se sostiene el contrato? Compila, tiene la principal y al menos un `post:` (regla 1)."""
    try:
        main = next((n for n in ast.parse(code).body if isinstance(n, ast.FunctionDef) and n.name == fn), None)
        compile(code, "<contrato>", "exec")
    except SyntaxError:
        return False
    return main is not None and bool(cp.condiciones(ast.get_docstring(main))[1])


def aviso(code: str, fn: str) -> str | None:
    """Si el contrato admite dos respuestas para una entrada, el mensaje con el testigo."""
    try:
        program, _ = compile_source(code)
    except SelloError:
        return None
    u = unique_program(program, {fn}).get(fn)
    if u is None or u.status != AMBIGUOUS:
        return None
    w = u.to_dict()["witness"]
    return (f"Your contract accepts two different results for {w['input']}: {w['results'][0]} and "
            f"{w['results'][1]}. If the task fixes the result for that input, make `ensures` say it. "
            f"If the task really leaves it open, or the input is outside what the task requires, keep "
            f"the contract as it is. Reply with the whole program in one ```sello block either way.")


def aviso_py(code: str, fn: str) -> str | None:
    """`aviso` para un contrato de Python: el testigo lo busca CrossHair (`contrato_py.ambiguo`)."""
    w = cp.ambiguo(code, fn)
    if w is None:
        return None
    args, r1, r2 = w
    return (f"Your contract accepts two different results for {fn}({', '.join(map(repr, args))}): {r1!r} and "
            f"{r2!r}. If the task fixes the result for that input, make the `post:` conditions say it. If "
            f"the task really leaves it open, or the input is outside what the task requires, keep the "
            f"contract as it is. Reply with the whole code in one ```python block either way.")


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


def run_one(p: dict, model: str, max_attempts: int, lang: str = "sello", con_aviso: bool = False) -> dict:
    prev: tuple[str, str] | None = None
    attempts: list[dict] = []
    accepted_at: int | None = None
    code = ""
    avisado = False
    for i in range(1, max_attempts + 1 + (1 if con_aviso else 0)):
        a = ask((prompt_py if lang == "python" else prompt)(p, prev), model)
        code = extract(a["text"], lang)
        ok, feedback, phase = (juez_debil_py if lang == "python" else juez_debil)(code, p)
        if ok and con_aviso and not avisado:
            avisado = True
            msg = (aviso_py if lang == "python" else aviso)(code, p["fn"])
            if msg:
                ok, feedback, phase = False, msg, "ambiguous"
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
        if i == max_attempts and not (phase == "ambiguous"):
            break  # el aviso es una vuelta de más; sin él, el tope de siempre
        prev = (code, feedback)
    return {"problem": p["fn"], "cond": COND_PY if lang == "python" else COND, "model": model,
            "accepted_at": accepted_at, "aviso": con_aviso,
            "avisado": [x["feedback"] for x in attempts if x["phase"] == "ambiguous"],
            "compila": (compila_py if lang == "python" else compila)(code, p["fn"]),
            "escribio_cuerpo": any(x["phase"] == "body" for x in attempts),
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
    ap.add_argument("--lang", choices=["sello", "python"], default="sello")
    ap.add_argument("--aviso", action="store_true", help="una vuelta con el testigo si el contrato es ambiguo (Sello: sello.unique; Python: CrossHair)")
    ap.add_argument("--tag", default="", help="sufijo del nombre de la corrida")
    args = ap.parse_args()
    probs = [json.loads(f.read_text()) for f in sorted(PROBLEMAS.glob("*.json"))]
    if args.only:
        probs = [p for p in probs if p["fn"] == args.only]
    when = dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    print(f"{len(probs)} problemas, modelo {args.model}, hasta {args.attempts} intentos", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        rows = list(ex.map(lambda p: run_one(p, args.model, args.attempts, args.lang, args.aviso), probs))
    RESULTADOS.mkdir(exist_ok=True)
    tag = f"contratos-{when}-{args.model}" + ("-py" if args.lang == "python" else "") \
        + ("-aviso" if args.aviso else "") + (f"-{args.tag}" if args.tag else "")
    base = RESULTADOS / (tag if not args.only else f"humo-{tag}")
    base.with_suffix(".jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    md = resumen(rows, args.model, when)
    base.with_suffix(".md").write_text(md)
    print(md)
    print(f"detalle: {base.with_suffix('.jsonl')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
