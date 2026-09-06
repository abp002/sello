#!/usr/bin/env python3
"""El probador sobre lo ya medido. Sin modelo.

Dos preguntas, sobre corridas anteriores del juez y de mutantes:

  1. Soluciones aceptadas (`juez-*.jsonl`, condiciones `sello*`): ¿cuántas funciones prueba el
     nivel 2, por qué no las demás, y encuentra algún bug real en una solución que el juez débil
     y el oráculo dieron por buena?
  2. Mutantes (`mutantes-*.jsonl`): de los que llegaron a producción (silenciosos, cazados,
     ruidosos) y de los equivalentes en el dominio, ¿cuántos mata el probador en compilación?

Cada programa pasa por `sello check` (compilador, ejemplos, probador) en un proceso aparte.

    uv run python bench/probador.py \\
        --soluciones bench/resultados/juez-2026-09-05-0015-haiku.jsonl \\
                     bench/resultados/juez-2026-09-05-0015-sonnet.jsonl \\
                     bench/resultados/juez-2026-09-05-1920-haiku-contrato.jsonl \\
        --mutantes bench/resultados/mutantes-2026-09-05-1931.jsonl
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import RESULTADOS, ROOT  # noqa: E402
from harness3 import CONDS_TODAS  # noqa: E402
from mutantes import CAZADO, EQUIVALENTE, RUIDOSO, SILENCIOSO  # noqa: E402

TIMEOUT = 120
MOTIVOS = ("undecided", "timeout", "termination", "mutual recursion", "unsupported", "not attempted", "z3")
LLEGAN = (CAZADO, RUIDOSO, SILENCIOSO)


def comprobar(code: str) -> dict:
    """`sello check` con el probador, en un proceso aparte. Devuelve el JSON que imprime."""
    with tempfile.TemporaryDirectory() as d:
        src = Path(d, "sol.sello")
        src.write_text(code + "\n")
        try:
            r = subprocess.run([sys.executable, "-m", "sello.cli", "check", str(src)],
                               capture_output=True, text=True, timeout=TIMEOUT, cwd=ROOT)
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": {"code": "E500", "what": f"timeout after {TIMEOUT}s"}}
    try:
        return json.loads(r.stdout.strip() or r.stderr.strip()[-1500:])
    except json.JSONDecodeError:
        return {"ok": False, "error": {"code": "E000", "what": (r.stdout + r.stderr)[-800:]}}


def motivo(unproven: str) -> str:
    """Agrupa el motivo de un unknown del probador."""
    for m in MOTIVOS:
        if unproven.startswith(m):
            return m
    return "undecided"


def evaluar(row: dict, check=comprobar) -> dict:
    """Pasa el programa por el compilador con el probador y resume: niveles por función, o el
    error (y si lo encontró el probador)."""
    t0 = time.time()
    r = check(row["code"])
    out = {k: v for k, v in row.items()}
    out["ms"] = int((time.time() - t0) * 1000)
    if r.get("ok"):
        out["ok"] = True
        out["error"] = None
        out["funciones"] = [{"name": f["name"], "level": f.get("level", 1),
                             "motivo": None if f.get("level") == 2 else motivo(f.get("unproven", ""))}
                            for f in r["functions"]]
        principal = next((f for f in out["funciones"] if f["name"] == row["problem"]), None)
        out["principal"] = principal["level"] if principal else None
    else:
        err = r.get("error", {})
        out["ok"] = False
        out["funciones"] = []
        out["principal"] = None
        out["error"] = {"code": err.get("code"), "what": err.get("what", "")[:300],
                        "probador": err.get("found_by") == "prover"}
    return out


# ---------- carga ----------

def soluciones(paths: list[Path], only: str | None) -> list[dict]:
    """Soluciones `sello*` aceptadas, una por (problema, condición, modelo); manda el último fichero."""
    sel: dict[tuple, dict] = {}
    for path in paths:
        for line in path.read_text().splitlines():
            r = json.loads(line)
            if r["cond"].startswith("sello") and r.get("code") and r.get("accepted_at") and (not only or r["problem"] == only):
                sel[(r["problem"], r["cond"], r["model"])] = {
                    "kind": "solucion", "problem": r["problem"], "cond": r["cond"], "model": r["model"],
                    "code": r["code"], "origen": path.name}
    return [sel[k] for k in sorted(sel)]


def mutantes(paths: list[Path], only: str | None) -> list[dict]:
    """Mutantes `sello*` que llegaron a producción o quedaron equivalentes en el dominio."""
    out: list[dict] = []
    for path in paths:
        for line in path.read_text().splitlines():
            r = json.loads(line)
            if not r["cond"].startswith("sello") or (only and r["problem"] != only):
                continue
            for m in r.get("mutantes", []):
                if m["cat"] in LLEGAN + (EQUIVALENTE,):
                    out.append({"kind": "mutante", "problem": r["problem"], "cond": r["cond"], "model": r["model"],
                                "cat": m["cat"], "op": m["op"], "desc": m["desc"], "code": m["code"], "origen": path.name})
    return out


# ---------- resumen ----------

def _pct(a: int, b: int) -> str:
    return f"{a}/{b} ({100 * a / b:.0f} %)" if b else "-"


def resumen(rows: list[dict], when: str) -> str:
    cols = sorted({(r["cond"], r["model"]) for r in rows}, key=lambda x: (CONDS_TODAS.index(x[0]), x[1]))
    name = lambda c: f"{c[0]}·{c[1]}"  # noqa: E731
    head = "| " + " | ".join(name(c) for c in cols) + " |"
    sep = "|---|" + "---|" * len(cols)
    out = [f"# El probador {when}", "",
           "Nivel 2 (Z3) sobre las soluciones que el juez débil ya aceptó y sobre los mutantes que "
           "llegaron a producción. Sin modelo: determinista y gratis.", ""]

    sols = [r for r in rows if r["kind"] == "solucion"]
    if sols:
        probs = sorted({r["problem"] for r in sols})
        by = {(r["problem"], r["cond"], r["model"]): r for r in sols}
        out += ["## Soluciones aceptadas", "",
                "Formato: nivel de la función principal · funciones en nivel 2 / total. `✗ Exxx` = el "
                "probador encontró una entrada que rompe el contrato: un bug real en una solución que el "
                "juez débil y el oráculo dieron por buena.", "", "| Problema " + head, sep]
        for pr in probs:
            cells = []
            for c in cols:
                r = by.get((pr, *c))
                if r is None:
                    cells.append("-")
                elif not r["ok"]:
                    cells.append(f"✗ {r['error']['code']}" + ("" if r["error"]["probador"] else " (herramienta)"))
                else:
                    n2 = sum(f["level"] == 2 for f in r["funciones"])
                    cells.append(f"{r['principal']} · {n2}/{len(r['funciones'])}")
            out.append(f"| {pr} | " + " | ".join(cells) + " |")
        out += ["", "| " + head, sep]

        def rs(c): return [r for r in sols if (r["cond"], r["model"]) == c]
        def fns(c): return [f for r in rs(c) for f in r["funciones"]]
        def stat(label, f): out.append(f"| {label} | " + " | ".join(f(c) for c in cols) + " |")
        stat("soluciones", lambda c: str(len(rs(c))))
        stat("**principal en nivel 2**", lambda c: f"**{_pct(sum(r['principal'] == 2 for r in rs(c)), len(rs(c)))}**")
        stat("funciones en nivel 2", lambda c: _pct(sum(f['level'] == 2 for f in fns(c)), len(fns(c))))
        for m, label in (("undecided", "· Z3 no decide"), ("timeout", "· sin tiempo"),
                         ("termination", "· sin medida de terminación"), ("mutual recursion", "· recursión mutua"),
                         ("unsupported", "· construcción no traducida"), ("not attempted", "· sin intentar (otra función falló)")):
            stat(label, lambda c, m=m: str(sum(f["motivo"] == m for f in fns(c))))
        stat("bugs reales en soluciones aceptadas", lambda c: str(sum(1 for r in rs(c) if not r["ok"] and r["error"]["probador"])))
        stat("fallos de la herramienta", lambda c: str(sum(1 for r in rs(c) if not r["ok"] and not r["error"]["probador"])))
        stat("tiempo total (s)", lambda c: f"{sum(r['ms'] for r in rs(c)) / 1000:.0f}")
        bugs = [r for r in sols if not r["ok"]]
        if bugs:
            out += ["", "Rechazadas:", ""]
            out += [f"- {r['problem']} ({name((r['cond'], r['model']))}): `{r['error']['code']}` {r['error']['what']}" for r in bugs]

    muts = [r for r in rows if r["kind"] == "mutante"]
    if muts:
        probs = sorted({r["problem"] for r in muts})
        out += ["", "## Mutantes", "",
                "De los mutantes que llegaron a producción en la corrida de mutantes (pasaron el juez débil "
                "y no son equivalentes en el dominio), cuántos mata ahora el probador en compilación. "
                "Formato: matados / llegaban · equivalentes matados / equivalentes (un equivalente matado "
                "es un bug fuera de los casos del oráculo).", "", "| Problema " + head, sep]

        def matado(r): return (not r["ok"]) and r["error"]["probador"]
        for pr in probs:
            cells = []
            for c in cols:
                ms = [r for r in muts if (r["problem"], r["cond"], r["model"]) == (pr, *c)]
                if not ms:
                    cells.append("-")
                    continue
                ll = [r for r in ms if r["cat"] in LLEGAN]
                eq = [r for r in ms if r["cat"] == EQUIVALENTE]
                cells.append(f"{sum(map(matado, ll))}/{len(ll)} · {sum(map(matado, eq))}/{len(eq)}")
            out.append(f"| {pr} | " + " | ".join(cells) + " |")
        out += ["", "| " + head, sep]

        def rs(c): return [r for r in muts if (r["cond"], r["model"]) == c]
        def cat(c, k): return [r for r in rs(c) if r["cat"] == k]
        def ll(c): return [r for r in rs(c) if r["cat"] in LLEGAN]
        def stat(label, f): out.append(f"| {label} | " + " | ".join(f(c) for c in cols) + " |")
        stat("llegaban a producción", lambda c: str(len(ll(c))))
        stat("**matados por el probador / llegaban**", lambda c: f"**{_pct(sum(map(matado, ll(c))), len(ll(c)))}**")
        stat("· de los cazados en producción (E201)", lambda c: _pct(sum(map(matado, cat(c, CAZADO))), len(cat(c, CAZADO))))
        stat("· de los ruidosos (E300 / E500)", lambda c: _pct(sum(map(matado, cat(c, RUIDOSO))), len(cat(c, RUIDOSO))))
        stat("· de los silenciosos", lambda c: _pct(sum(map(matado, cat(c, SILENCIOSO))), len(cat(c, SILENCIOSO))))
        stat("equivalentes en el dominio matados (bug fuera del oráculo)", lambda c: _pct(sum(map(matado, cat(c, EQUIVALENTE))), len(cat(c, EQUIVALENTE))))
        for code in ("E201", "E300", "E500"):
            stat(f"· matados con {code}", lambda c, code=code: str(sum(1 for r in rs(c) if matado(r) and r["error"]["code"] == code)))
        stat("fallos de la herramienta", lambda c: str(sum(1 for r in rs(c) if not r["ok"] and not r["error"]["probador"])))
        stat("tiempo total (s)", lambda c: f"{sum(r['ms'] for r in rs(c)) / 1000:.0f}")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--soluciones", nargs="*", type=Path, default=[], help="corridas del juez (jsonl)")
    ap.add_argument("--mutantes", nargs="*", type=Path, default=[], help="corridas de mutantes (jsonl)")
    ap.add_argument("--only", help="nombre de un problema")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    if not args.soluciones and not args.mutantes:
        ap.error("hace falta --soluciones y/o --mutantes")
    rows = soluciones(args.soluciones, args.only) + mutantes(args.mutantes, args.only)
    when = dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    print(f"{len(rows)} programas, {args.workers} workers", file=sys.stderr)

    def run(r: dict) -> dict:
        out = evaluar(r)
        tag = "ok" if out["ok"] else f"✗ {out['error']['code']}" + (" probador" if out["error"]["probador"] else "")
        extra = f" nivel {out['principal']}" if out["ok"] and r["kind"] == "solucion" else ""
        print(f"  {r['kind']:<9} {r['problem']:<15} {r['cond']:<15} {r['model']:<7} {r.get('cat', ''):<12} "
              f"{tag}{extra} ({out['ms']} ms)", file=sys.stderr, flush=True)
        return out

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        done = list(ex.map(run, rows))

    RESULTADOS.mkdir(exist_ok=True)
    base = RESULTADOS / (("humo-" if args.only else "") + f"probador-{when}")
    with open(base.with_suffix(".jsonl"), "w") as f:
        for r in done:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    md = resumen(done, when)
    base.with_suffix(".md").write_text(md)
    print(md)
    print(f"detalle: {base.with_suffix('.jsonl')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
