#!/usr/bin/env python3
"""Fase 4: el benchmark de vericoding en Sello. Con modelo.

Condición `sello_contrato` con el contrato del benchmark: la spec Dafny traducida por
`traducir.py` (firma, `requires`, `ensures` de la principal y los helpers recursivos
congelados). El modelo escribe el cuerpo y los `example` de la principal (el benchmark no trae
casos). Cada intento pasa por `contrato.violacion` (¿respeta el contrato?) y por `sello check`
(compila, ejemplos, probador). Lo que compila pero no se prueba vuelve al modelo con el motivo
(`unproven`), como en el benchmark vuelve el error del verificador.

Éxito («el verificador acepta»): la principal y todo lo que llama, transitivamente, en nivel 2.
Los helpers congelados no cuentan: su contrato es su definición y se dan por buenos (se anota
cuántos quedan en nivel 1). Segunda columna: nivel 1 (compila y pasa sus ejemplos).

    uv run python bench/vericoding/harness4.py --model haiku --muestra 50 --semilla 1
    uv run python bench/vericoding/harness4.py --model haiku --only DA0003 DD0042   # humo
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BENCH = AQUI.parent
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(BENCH.parent))
import contrato as ct  # noqa: E402
from harness import RESULTADOS, SPEC, ask, extract  # noqa: E402
from probador import MOTIVOS, comprobar, motivo  # noqa: E402
from traducir import FUENTES, TAREAS, Tarea  # noqa: E402
from traducir import contrato as contrato_de  # noqa: E402

from sello.hash import callees  # noqa: E402
from sello.parser import parse  # noqa: E402

COND = "sello_contrato"


# ---------- prompt ----------

def prompt(t: Tarea, c: ct.Contrato, prev: tuple[str, str, str] | None) -> str:
    head = (f"Below is the complete specification of Sello, a small programming language.\n\n"
            f"{SPEC}\n\n---\n\n"
            f"Task: complete the Sello program below so that it defines `{t.sello}`. "
            f"The contract is fixed and was written by someone else: the signature, `requires`, `ensures` "
            f"and `effects` lines of `{t.fn}`, and the helper functions shown, must appear unchanged in "
            f"your program. Write the body of `{t.fn}` and add at least one `example` line to it (the "
            f"contract has none). You may add helper functions of your own; every function needs its "
            f"contract clauses.\n"
            f"Your program is accepted only when the compiler proves the contract of `{t.fn}` for every "
            f"input (verification level 2), and the same for every helper you add that `{t.fn}` calls. "
            f"If it compiles but the prover cannot decide, you get the reason back: restructure the body "
            f"(small helpers whose `ensures` say exactly what the caller needs, an argument that decreases "
            f"in every recursive call) until it proves.\n\n"
            f"```sello\n{c.texto}\n```\n\n"
            f"Reply with one ```sello block containing the whole program.")
    if prev is None:
        return head
    code, err, fase = prev
    if fase == "unproven":
        why = ("It compiled and passed its examples, but the prover could not certify it, and only a proven "
               "program is accepted. Functions at level 1 and why:")
    else:
        why = "It was rejected:"
    return (f"{head}\n\nYour previous program:\n```sello\n{code}\n```\n\n{why}\n```\n{err}\n```\n\n"
            f"Fix it and reply with the whole corrected program in one ```sello block.")


# ---------- veredicto ----------

def cierre(code: str, fn: str, congelados: set[str]) -> set[str] | None:
    """`fn` y lo que llama, transitivamente, sin entrar en los helpers congelados. None si no parsea."""
    try:
        prog = parse(code)
    except Exception:
        return None
    fns = {f.name: f for f in prog.fns}
    out: set[str] = set()
    pendientes = [fn]
    while pendientes:
        n = pendientes.pop()
        if n in out or n not in fns or n in congelados:
            continue
        out.add(n)
        pendientes += sorted(callees(fns[n]))
    return out


def veredicto(r: dict, code: str, fn: str, congelados: set[str]) -> dict:
    """De la salida de `sello check`: fase (compile | unproven | proven), niveles y motivos."""
    if not r.get("ok"):
        return {"fase": "compile", "error": r.get("error", {})}
    niveles = {f["name"]: f.get("level", 1) for f in r["functions"]}
    razones = {f["name"]: f.get("unproven", "") for f in r["functions"]}
    cc = cierre(code, fn, congelados) or {fn}
    sin_probar = sorted(n for n in cc if niveles.get(n, 1) != 2)
    return {"fase": "proven" if not sin_probar else "unproven", "niveles": niveles,
            "principal": niveles.get(fn, 1), "sin_probar": sin_probar,
            "motivos": {n: razones.get(n, "") for n in sin_probar},
            "congelados_sin_probar": sorted(n for n in congelados if niveles.get(n, 1) != 2)}


# ---------- una corrida ----------

def run_one(t: Tarea, model: str, max_attempts: int) -> dict:
    c = contrato_de(t)
    congelados = set(t.helpers)
    prev: tuple[str, str, str] | None = None
    attempts: list[dict] = []
    accepted_at = principal_at = proven_at = None
    code, ultimo = "", {}
    for i in range(1, max_attempts + 1):
        a = ask(prompt(t, c, prev), model)
        code = extract(a["text"], "sello")
        v = ct.violacion(c, code)
        vd: dict = {}
        if v:
            fase, feedback = "contract", v
        else:
            vd = veredicto(comprobar(code), code, t.fn, congelados)
            fase = vd["fase"]
            if fase == "compile":
                feedback = json.dumps({"ok": False, "error": vd["error"]}, ensure_ascii=False)
            elif fase == "unproven":
                feedback = "\n".join(f"{n}: {m or 'level 1'}" for n, m in vd["motivos"].items())
            else:
                feedback = ""
            if fase in ("unproven", "proven"):
                accepted_at = accepted_at or i
                ultimo = vd
                if vd["principal"] == 2:
                    principal_at = principal_at or i
            if fase == "proven":
                proven_at = i
        m = re.search(r'"code":\s*"(E\d{3})"', feedback) if fase == "compile" else None
        attempts.append({"n": i, "fase": fase, "sello_error": m.group(1) if m else None,
                         "sin_probar": vd.get("sin_probar"), "motivos": vd.get("motivos"),
                         "cost": a["cost"], "tokens_in": a["tokens_in"], "tokens_out": a["tokens_out"],
                         "thinking": a.get("thinking", 0), "ms": a["ms"], "code": code, "feedback": feedback[:2000]})
        print(f"  {t.id} {t.fn:<24} intento {i}: {fase}" + (f" {m.group(1)}" if m else "")
              + (f" ({', '.join(motivo(x) for x in vd['motivos'].values())})" if fase == "unproven" else ""),
              file=sys.stderr, flush=True)
        if fase == "proven":
            break
        prev = (code, feedback, fase)
    return {"problem": t.id, "fn": t.fn, "source": t.source, "cond": COND, "model": model,
            "accepted_at": accepted_at, "principal_proven_at": principal_at, "proven_at": proven_at,
            "attempts": len(attempts), "cost": sum(x["cost"] for x in attempts),
            "tokens_in": sum(x["tokens_in"] for x in attempts), "tokens_out": sum(x["tokens_out"] for x in attempts),
            "thinking": sum(x["thinking"] for x in attempts), "ms": sum(x["ms"] for x in attempts),
            "code": code if accepted_at else None, "helpers": t.helpers,
            "congelados_sin_probar": ultimo.get("congelados_sin_probar", []), "notas": t.notas,
            "ultimo_motivo": (next(iter(ultimo["motivos"].values()), "") if ultimo and ultimo["fase"] == "unproven" else ""),
            "detail": attempts}


# ---------- resumen ----------

def _pct(a: int, b: int) -> str:
    return f"{a}/{b} ({100 * a / b:.0f} %)" if b else "-"


def resumen(rows: list[dict], model: str, when: str) -> str:
    fuentes = [f for f in FUENTES if any(r["source"] == f for r in rows)]
    out = [f"# Vericoding en Sello {when} · modelo `{model}` · condición `{COND}`", "",
           "El contrato lo escribe el benchmark (traducido de Dafny); el modelo escribe el cuerpo y sus ejemplos. "
           "Por tarea: `2 (k)` = probada (la principal y lo que llama en nivel 2) al intento k · `1 (k)` = compila y "
           "pasa sus ejemplos al intento k pero no se prueba · `✗ (n)` = no compila en n intentos.", "",
           "| tarea | fuente | fn | resultado | último motivo sin probar |", "|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: r["problem"]):
        if r["proven_at"]:
            res = f"2 ({r['proven_at']})"
        elif r["accepted_at"]:
            res = f"1 ({r['accepted_at']})"
        else:
            res = f"✗ ({r['attempts']})"
        m = r.get("ultimo_motivo", "")
        out.append(f"| {r['problem']} | {r['source']} | {r['fn']} | {res} | {m[:70]} |")

    def rs(f): return [r for r in rows if f is None or r["source"] == f]
    cols = fuentes + [None]
    out += ["", "| | " + " | ".join(f or "total" for f in cols) + " |", "|---|" + "---|" * len(cols)]

    def stat(label, f): out.append(f"| {label} | " + " | ".join(f(rs(c)) for c in cols) + " |")
    stat("tareas", lambda x: str(len(x)))
    stat("**probadas (nivel 2)**", lambda x: f"**{_pct(sum(1 for r in x if r['proven_at']), len(x))}**")
    stat("· a la primera", lambda x: str(sum(1 for r in x if r["proven_at"] == 1)))
    stat("· media de intentos hasta probar", lambda x: f"{sum(r['proven_at'] for r in x if r['proven_at']) / max(1, sum(1 for r in x if r['proven_at'])):.2f}")
    stat("principal en nivel 2", lambda x: _pct(sum(1 for r in x if r["principal_proven_at"]), len(x)))
    stat("aceptadas (nivel 1)", lambda x: _pct(sum(1 for r in x if r["accepted_at"]), len(x)))
    stat("· media de intentos hasta aceptar", lambda x: f"{sum(r['accepted_at'] for r in x if r['accepted_at']) / max(1, sum(1 for r in x if r['accepted_at'])):.2f}")
    stat("tareas con helpers congelados", lambda x: str(sum(1 for r in x if r["helpers"])))
    stat("· con alguno sin probar", lambda x: str(sum(1 for r in x if r["congelados_sin_probar"])))
    stat("tokens de salida", lambda x: str(sum(r["tokens_out"] for r in x)))
    stat("de ellos, razonamiento", lambda x: str(sum(r.get("thinking", 0) for r in x)))
    stat("tokens de entrada", lambda x: str(sum(r["tokens_in"] for r in x)))
    stat("coste USD", lambda x: f"{sum(r['cost'] for r in x):.3f}")
    stat("tiempo total (s)", lambda x: f"{sum(r['ms'] for r in x) / 1000:.0f}")

    fases: dict[str, int] = {}
    for r in rows:
        for a in r["detail"]:
            k = a["sello_error"] or a["fase"]
            if k != "proven":
                fases[k] = fases.get(k, 0) + 1
    if fases:
        out += ["", "Rechazos por causa (todos los intentos):", ""]
        out += [f"- `{k}`: {v}" for k, v in sorted(fases.items(), key=lambda kv: -kv[1])]
    motivos: dict[str, int] = {}
    for r in rows:
        if r["accepted_at"] and not r["proven_at"]:
            m = motivo(r.get("ultimo_motivo", "")) if r.get("ultimo_motivo") else "undecided"
            motivos[m] = motivos.get(m, 0) + 1
    if motivos:
        out += ["", "Por qué no se prueban las aceptadas (último intento):", ""]
        out += [f"- {k}: {v}" for k, v in sorted(motivos.items(), key=lambda kv: -kv[1])]
    return "\n".join(out) + "\n"


def cargar(ids: list[str] | None) -> list[Tarea]:
    out = [Tarea.from_dict(json.loads(f.read_text())) for f in sorted(TAREAS.glob("*.json"))]
    if ids:
        faltan = set(ids) - {t.id for t in out}
        if faltan:
            raise SystemExit(f"no hay tarea traducida para: {', '.join(sorted(faltan))}")
        out = [t for t in out if t.id in ids]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--only", nargs="*", help="ids de tareas (humo)")
    ap.add_argument("--muestra", type=int, help="tantas tareas al azar, con --semilla")
    ap.add_argument("--semilla", type=int, default=1)
    ap.add_argument("--attempts", type=int, default=5)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    tareas = cargar(args.only)
    if args.muestra and not args.only:
        tareas = sorted(random.Random(args.semilla).sample(tareas, min(args.muestra, len(tareas))), key=lambda t: t.id)
    when = dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    print(f"{len(tareas)} tareas, modelo {args.model}, hasta {args.attempts} intentos", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        rows = list(ex.map(lambda t: run_one(t, args.model, args.attempts), tareas))
    RESULTADOS.mkdir(exist_ok=True)
    tag = f"vericoding-{when}-{args.model}" + (f"-muestra{args.muestra}-semilla{args.semilla}" if args.muestra and not args.only else "")
    base = RESULTADOS / (tag if not args.only else f"humo-{tag}")
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
