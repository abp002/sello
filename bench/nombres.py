#!/usr/bin/env python3
"""¿El veredicto del probador depende de cómo se llaman las funciones? Sin modelo.

El almacén enlaza lo que llama un programa renombrado a `f_<hash>`, y los símbolos de Z3 llevan
ese nombre (`fn!f_<hash>`). El nombre cambia el orden en que `_setup` mete los axiomas y las
heurísticas de Z3; en los contraejemplos ya se vio (nota 'Un candidato que no se reproduce no
cierra la búsqueda'). Aquí se mide en todo: cada programa pasa por `sello check` con tres
juegos de nombres, que dejan el mismo programa (los hashes no cambian, y se comprueba):

- `O`: los nombres del fichero.
- `H`: cada función como `f_<hash corto>`, como la enlaza el almacén.
- `X`: un renombrado arbitrario de control, `g_<sha de su nombre>`, que no es el del almacén.

Y compara el veredicto función a función: nivel y, si no es 2, el motivo; si el programa no
pasa, el error. Cada esquema corre `--repeticiones` veces, intercalado programa a programa, para
separar lo que depende del nombre de lo que depende del reloj.

    .venv/bin/python bench/nombres.py --programas bench/resultados/probador-...jsonl [...] \\
        --vericoding bench/resultados/vericoding-...jsonl [...] --etiqueta X

Escribe `nombres-<fecha>-<etiqueta>.{jsonl,md}` en bench/resultados.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(AQUI / "vericoding"))

from harness import RESULTADOS  # noqa: E402
from probador import comprobar  # noqa: E402
from reprobar import Carga  # noqa: E402

from sello.hash import hash_program, short  # noqa: E402
from sello.lexer import lex  # noqa: E402
from sello.parser import parse  # noqa: E402

ESQUEMAS = ("O", "H", "X")


# ---------- el renombrado ----------

def nombres(code: str, esquema: str) -> dict[str, str]:
    """{nombre del fichero: nombre nuevo} de cada función definida."""
    program = parse(code)
    if esquema == "O":
        return {f.name: f.name for f in program.fns}
    if esquema == "H":
        return {n: f"f_{short(h)}" for n, h in hash_program(program).items()}
    if esquema == "X":
        return {f.name: "g_" + hashlib.sha256(f"x:{f.name}".encode()).hexdigest()[:12] for f in program.fns}
    raise ValueError(esquema)


def renombrar(code: str, mapa: dict[str, str]) -> str:
    """Reescribe el texto: cada nombre de función definida tras `fn` o delante de `(`. Una
    variable que se llame como una función no va delante de `(`: se queda."""
    toks = lex(code)
    lineas = code.split("\n")
    cambios: dict[int, list] = defaultdict(list)
    for i, t in enumerate(toks):
        if t.kind != "NAME" or t.value not in mapa:
            continue
        tras_fn = i > 0 and toks[i - 1].kind == "KW" and toks[i - 1].value == "fn"
        llamada = i + 1 < len(toks) and toks[i + 1].kind == "SYM" and toks[i + 1].value == "("
        if tras_fn or llamada:
            cambios[t.line].append(t)
    for ln, ts in cambios.items():
        s = lineas[ln - 1]
        for t in sorted(ts, key=lambda t: -t.col):  # de derecha a izquierda: las columnas no se mueven
            s = s[:t.col - 1] + mapa[t.value] + s[t.end_col - 1:]
        lineas[ln - 1] = s
    return "\n".join(lineas)


def variante(code: str, esquema: str) -> tuple[str, dict[str, str]] | None:
    """El programa con ese juego de nombres y el mapa de vuelta, o None si no sería el mismo
    programa: dos funciones con el mismo nombre nuevo (iguales en contenido, en `H`) o algún
    hash distinto tras renombrar."""
    mapa = nombres(code, esquema)
    if len(set(mapa.values())) != len(mapa):
        return None
    nuevo = renombrar(code, mapa)
    antes = hash_program(parse(code))
    despues = hash_program(parse(nuevo))
    if {mapa[n]: h for n, h in antes.items()} != despues:
        return None
    return nuevo, {v: k for k, v in mapa.items()}


# ---------- el veredicto ----------

def veredicto(r: dict, vuelta: dict[str, str]) -> dict:
    """Lo comparable de la salida de `sello check`, con los nombres del fichero."""
    if r.get("ok"):
        return {"ok": True, "funciones": {
            vuelta.get(f["name"], f["name"]): {"level": f.get("level", 1), "unproven": f.get("unproven", "")}
            for f in r["functions"]}}
    err = r.get("error", {})
    return {"ok": False, "error": {"code": err.get("code"), "probador": err.get("found_by") == "prover",
                                   "what": (err.get("what") or "")[:300]}}


def clave(v: dict, fn: str | None = None) -> str:
    """Lo que tiene que coincidir entre esquemas: el nivel (y si es 2, nada más) o el error.
    El motivo de un nivel 1 no entra: «undecided» frente a «timeout» no cambia el certificado."""
    if not v["ok"]:
        return f"error {v['error']['code']}{' probador' if v['error']['probador'] else ''}"
    return f"nivel {v['funciones'][fn]['level']}"


def reloj(v: dict, fn: str) -> bool:
    return v["ok"] and "(wall clock)" in v["funciones"][fn]["unproven"]


# ---------- corpus ----------

def corpus(programas: list[Path], vericoding: list[Path]) -> list[dict]:
    out: list[dict] = []
    for path in programas:
        for i, line in enumerate(path.read_text().splitlines()):
            r = json.loads(line)
            out.append({"id": f"{path.name}:{i}", "kind": r["kind"], "problem": r["problem"], "cond": r["cond"],
                        "model": r["model"], "code": r["code"]})
    for path in vericoding:
        for line in path.read_text().splitlines():
            r = json.loads(line)
            for a in r.get("detail", []):
                if a.get("fase") in ("unproven", "proven") and a.get("code"):
                    out.append({"id": f"{path.name}:{r['problem']}:{a['n']}", "kind": "vericoding",
                                "problem": r["problem"], "cond": "vericoding", "model": r["model"], "code": a["code"]})
    return out


# ---------- comparación ----------

def comparar(rows: list[dict]) -> dict:
    """Por (programa, función): la clave de cada esquema y repetición, y qué la mueve."""
    por: dict[str, dict] = defaultdict(lambda: defaultdict(dict))
    for r in rows:
        if r["veredicto"] is not None:
            por[r["id"]][r["esquema"]][r["rep"]] = r["veredicto"]
    out = {"programas": len(por), "descartados": sorted({r["id"] for r in rows if r["veredicto"] is None}),
           "funciones": 0, "por_nombres": [], "por_reloj": [], "inestables": []}
    for pid, esq in por.items():
        if set(esq) != set(ESQUEMAS):
            continue
        todas = [v for e in esq.values() for v in e.values()]
        if all(not v["ok"] for v in todas):
            fns = [None]
        else:
            fns = sorted(set().union(*[v["funciones"] for v in todas if v["ok"]]))
        for fn in fns:
            out["funciones"] += 1
            k = {e: {rep: clave(v, fn) if v["ok"] else clave(v) for rep, v in reps.items()}
                 for e, reps in esq.items()}
            if len({x for reps in k.values() for x in reps.values()}) == 1:
                continue
            fila = {"id": pid, "fn": fn, "claves": k}
            hay_reloj = fn is not None and any(reloj(v, fn) for e in esq.values() for v in e.values())
            estable = all(len(set(reps.values())) == 1 for reps in k.values())
            if hay_reloj:
                out["por_reloj"].append(fila)
            elif estable:
                out["por_nombres"].append(fila)
            else:
                out["inestables"].append(fila)
    return out


def _nivel(k: str) -> int:
    return 2 if k == "nivel 2" else 0 if k.startswith("error") else 1


def resumen(rows: list[dict], cmp: dict, when: str, etiqueta: str, carga: list[str], segundos: dict) -> str:
    out = [f"# Nombres {when} ({etiqueta})", "",
           "Cada programa con sus nombres (O), renombrado a `f_<hash>` como lo enlaza el almacén (H) y con "
           "un renombrado arbitrario (X). Mismo programa (mismos hashes), mismo probador. Sin modelo.", "",
           f"Programas: {cmp['programas']} · funciones comparadas: {cmp['funciones']} · "
           f"descartados (el renombrado no conservaba los hashes o daba nombres repetidos): {len(cmp['descartados'])}", ""]
    dir_ = Counter()
    for f in cmp["por_nombres"]:
        o = next(iter(f["claves"]["O"].values()))
        for e in ("H", "X"):
            x = next(iter(f["claves"][e].values()))
            if x != o:
                dir_[(e, "gana" if _nivel(x) > _nivel(o) else "pierde" if _nivel(x) < _nivel(o) else "otro")] += 1
    out += ["| | H frente a O | X frente a O |", "|---|---|---|"]
    for d in ("pierde", "gana", "otro"):
        out.append(f"| {d} | {dir_[('H', d)]} | {dir_[('X', d)]} |")
    out += ["", f"Funciones distintas y estables en todas las repeticiones, sin reloj: **{len(cmp['por_nombres'])}**. "
            f"Con «(wall clock)» en alguna: {len(cmp['por_reloj'])}. Distintas e inestables sin reloj: {len(cmp['inestables'])}.", ""]
    for titulo, lista in (("Por nombres", cmp["por_nombres"]), ("Inestables, sin reloj", cmp["inestables"]),
                          ("Con reloj", cmp["por_reloj"])):
        if not lista:
            continue
        out += [f"## {titulo}", "", "| programa | función | O | H | X |", "|---|---|---|---|---|"]
        for f in lista:
            cel = [" / ".join(f["claves"][e][r] for r in sorted(f["claves"][e])) for e in ESQUEMAS]
            out.append(f"| {f['id']} | {f['fn'] or '-'} | " + " | ".join(cel) + " |")
        out.append("")
    out += ["## Coste y carga", "", "| esquema | segundos de `check` sumados |", "|---|---|"]
    out += [f"| {e} | {segundos.get(e, 0):.0f} |" for e in ESQUEMAS]
    out += ["", "Carga: " + ", ".join(carga), ""]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--programas", nargs="*", type=Path, default=[], help="salidas de probador.py (jsonl, con code)")
    ap.add_argument("--vericoding", nargs="*", type=Path, default=[], help="corridas de harness4 (jsonl)")
    ap.add_argument("--repeticiones", type=int, default=2)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--etiqueta", required=True)
    args = ap.parse_args()

    progs = corpus(args.programas, args.vericoding)
    tareas = [(p, e, rep) for rep in range(1, args.repeticiones + 1) for p in progs for e in ESQUEMAS]
    when = dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    base = RESULTADOS / f"nombres-{when}-{args.etiqueta}"
    print(f"{len(progs)} programas x {len(ESQUEMAS)} esquemas x {args.repeticiones} -> {base}.jsonl", flush=True)

    import time
    segundos: Counter = Counter()

    def run(t) -> dict:
        p, e, rep = t
        fila = {"id": p["id"], "kind": p["kind"], "problem": p["problem"], "cond": p["cond"], "model": p["model"],
                "esquema": e, "rep": rep, "veredicto": None}
        v = variante(p["code"], e)
        if v is None:
            return fila
        t0 = time.time()
        fila["veredicto"] = veredicto(comprobar(v[0]), v[1])
        fila["ms"] = int((time.time() - t0) * 1000)
        segundos[e] += fila["ms"] / 1000
        return fila

    carga = Carga()
    rows: list[dict] = []
    with ThreadPoolExecutor(args.workers) as ex, open(f"{base}.jsonl", "w") as fh:
        for i, r in enumerate(ex.map(run, tareas), 1):
            rows.append(r)
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            if i % 300 == 0:
                print(f"  {i}/{len(tareas)}", flush=True)
    cmp = comparar(rows)
    Path(f"{base}.md").write_text(resumen(rows, cmp, when, args.etiqueta, carga.cierra(), segundos))
    print(f"{len(cmp['por_nombres'])} por nombres, {len(cmp['por_reloj'])} con reloj, {len(cmp['inestables'])} inestables",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
