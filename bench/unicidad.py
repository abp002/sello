#!/usr/bin/env python3
"""¿Fija el contrato una sola respuesta? Dos corpus, sin modelo (SEL-8).

A: las tareas de vericoding (`vericoding/tareas/`), la función objetivo, con el contrato traducido
de Dafny. B: las soluciones de Sello de las corridas de mutantes, una vez por código distinto, la
función principal, con sus silenciosos. Cada función se juzga en su proceso (`sello.unique`) y dos
veces: lo que cambia de veredicto entre las dos es inestable (SEL-5) y se cuenta aparte.
Prerregistrado en el vault: 'Z3 dice si el contrato fija una sola respuesta'.

    .venv/bin/python bench/unicidad.py                      # todo
    .venv/bin/python bench/unicidad.py --solo B --limite 5  # humo
"""

from __future__ import annotations

import argparse
import glob
import json
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
BENCH = RAIZ / "bench"
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(BENCH))
from cotas import solo_cotas  # noqa: E402
from sello.parser import parse  # noqa: E402

RELOJ = 180  # segundos por función: red; lo que decide es el trabajo de Z3


def juzgar(src: str, fn: str) -> dict:
    cmd = [sys.executable, "-m", "sello.unique", "--only", fn]
    try:
        r = subprocess.run(cmd, input=src, capture_output=True, text=True, timeout=RELOJ, cwd=str(RAIZ))
    except subprocess.TimeoutExpired:
        return {"status": "unknown", "reason": "hung", "ms": RELOJ * 1000, "witness": None}
    for line in r.stdout.splitlines():
        d = json.loads(line)
        if "fatal" in d:
            return {"status": "unknown", "reason": f"fatal: {d['fatal']}", "ms": 0, "witness": None}
        if d.get("name") == fn:
            return {k: d[k] for k in ("status", "reason", "ms", "witness")}
    return {"status": "unknown", "reason": f"crashed: {r.stderr.strip()[-200:]}", "ms": 0, "witness": None}


def corpus_a() -> list[dict]:
    out = []
    for f in sorted((BENCH / "vericoding" / "tareas").glob("*.json")):
        d = json.loads(f.read_text())
        out.append({"corpus": "A", "id": d["id"], "fn": d["fn"], "src": d["esqueleto"]})
    return out


def corpus_b() -> list[dict]:
    por_codigo: dict[str, dict] = {}
    for f in sorted(glob.glob(str(BENCH / "resultados" / "mutantes-2026-09-0*.jsonl"))):
        for line in open(f):
            r = json.loads(line)
            if r["cond"] != "sello":
                continue
            rc = r["recuento"]
            fila = por_codigo.setdefault(r["code"], {
                "corpus": "B", "id": f"{r['problem']}·{r['model']}·{len(por_codigo)}", "fn": r["problem"],
                "src": r["code"], "silencioso": rc["silencioso"], "llegan": rc["llegan"],
                "origen": [], "cotas": solo_cotas(next(x for x in parse(r["code"]).fns if x.name == r["problem"]))})
            fila["origen"].append(Path(f).name)
            if (rc["silencioso"], rc["llegan"]) != (fila["silencioso"], fila["llegan"]):
                fila["aviso"] = "mismo código, otro recuento de mutantes"  # no debería pasar
                fila["silencioso"] = max(fila["silencioso"], rc["silencioso"])
    return list(por_codigo.values())


def tabla(filas: list[dict], titulo: str) -> list[str]:
    c = Counter(f["status"] for f in filas)
    n = len(filas) or 1
    out = [f"### {titulo} ({len(filas)})", "", "| veredicto | n | % |", "|---|---|---|"]
    for k in ("unique", "ambiguous", "unknown", "inestable"):
        out.append(f"| {k} | {c[k]} | {100 * c[k] / n:.0f} % |")
    razones = Counter(f["reason"].split(":")[0] for f in filas if f["status"] == "unknown")
    if razones:
        out += ["", "unknown por motivo: " + ", ".join(f"{k or '?'} {v}" for k, v in razones.most_common())]
    return out + [""]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", choices=["A", "B"])
    ap.add_argument("--limite", type=int)
    ap.add_argument("--hilos", type=int, default=4)
    a = ap.parse_args()
    filas = ([] if a.solo == "B" else corpus_a()) + ([] if a.solo == "A" else corpus_b())
    if a.limite:
        filas = [f for c in "AB" for f in [x for x in filas if x["corpus"] == c][:a.limite]]
    sello = time.strftime("%Y-%m-%d-%H%M")
    t0 = time.monotonic()

    def una(f: dict) -> dict:
        v1, v2 = juzgar(f["src"], f["fn"]), juzgar(f["src"], f["fn"])
        f["corridas"] = [v1, v2]
        f["status"] = v1["status"] if v1["status"] == v2["status"] else "inestable"
        f["reason"] = v1["reason"] if v1["status"] == "unknown" else v2["reason"]
        f["witness"] = v1["witness"] or v2["witness"]
        print(f"{f['corpus']} {f['id']:<28} {f['status']:<10} {f['reason'][:60]}", flush=True)
        return f

    with ThreadPoolExecutor(a.hilos) as ex:
        filas = list(ex.map(una, filas))

    nombre = f"unicidad-{sello}" + ("-humo" if a.limite else "")
    with open(BENCH / "resultados" / f"{nombre}.jsonl", "w") as fh:
        for f in filas:
            fh.write(json.dumps({k: v for k, v in f.items() if k != "src"}, ensure_ascii=False) + "\n")

    A = [f for f in filas if f["corpus"] == "A"]
    B = [f for f in filas if f["corpus"] == "B"]
    md = [f"# Unicidad del contrato {sello}", "",
          "Prerregistrado en el vault: 'Z3 dice si el contrato fija una sola respuesta'. Cada función, dos "
          f"veces; lo que cambia entre las dos es inestable. {time.monotonic() - t0:.0f} s.", ""]
    md += tabla(A, "A · vericoding, contrato humano")
    md += tabla(B, "B · soluciones de Sello, contrato de modelo")
    if B:
        con_sil = [f for f in B if f["silencioso"] > 0]
        control = [f for f in B if f["status"] == "unique" and f["silencioso"] > 0]
        cot = [f for f in B if f["cotas"]]
        md += ["### Contra los mutantes (B)", "",
               f"- **Control** · `unique` con silenciosos: {len(control)} "
               + (f"({', '.join(f['id'] for f in control)})" if control else "(0: el instrumento no se contradice)"),
               f"- Con al menos un silencioso: {len(con_sil)}; de ellas "
               + ", ".join(f"{k} {v}" for k, v in Counter(f['status'] for f in con_sil).most_common()),
               f"- `ambiguous` con algún silencioso: {sum(1 for f in B if f['status'] == 'ambiguous' and f['silencioso'] > 0)}"
               f" de {sum(1 for f in B if f['status'] == 'ambiguous')}",
               f"- Solo cotas (`cotas.py`): {len(cot)}; de ellas "
               + ", ".join(f"{k} {v}" for k, v in Counter(f['status'] for f in cot).most_common()),
               "", "| solución | veredicto | silenciosos/llegan | cotas | testigo |", "|---|---|---|---|---|"]
        for f in sorted(B, key=lambda f: f["id"]):
            w = f["witness"]
            ws = f"`{w['input']}` → {' / '.join(w['results'])}" if w else f.get("reason", "")
            md.append(f"| {f['id']} | {f['status']} | {f['silencioso']}/{f['llegan']} | "
                      f"{'sí' if f['cotas'] else ''} | {ws.replace('|', '¦')} |")
        md.append("")
    (BENCH / "resultados" / f"{nombre}.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    sys.exit(main())
