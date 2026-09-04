#!/usr/bin/env python3
"""Ensures solo de cotas: cuántas funciones principales acotan el resultado sin decir nada de él.

Recuento determinista sobre las soluciones aceptadas de corridas del juez (condición
`sello`). Una cláusula es *cota* si es una comparación cuyos dos lados se componen solo
de `result`, literales, parámetros, `len(...)` y aritmética; `and`/`or`/`not` de cotas
sigue siendo cota. Todo lo demás (`contains`, `count`, `forall`, `exists`, `distinct`,
`sorted`, una llamada a un `fn` del fichero) es *contenido*. Prerregistrado en el vault:
'Un ensures de cotas no certifica nada'.

También lista, por corrida, las veces que un modelo cambió el `ensures` de una función
tras recibir un `E201` (regla 3 de la nota).

    uv run python bench/cotas.py bench/resultados/juez-2026-09-02-2237-haiku.jsonl ...
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sello.nodes import Binary, BoolLit, Call, Expr, Fn, IntLit, Name, Unary  # noqa: E402
from sello.parser import parse  # noqa: E402
from sello.pretty import unparse  # noqa: E402

COMPARACIONES = {"<", "<=", ">", ">=", "==", "!="}
ARITMETICA = {"+", "-", "*", "/", "%"}


def es_aritmetica(e: Expr) -> bool:
    """Solo `result`, literales, nombres (parámetros), `len(nombre)` y aritmética."""
    if isinstance(e, (IntLit, BoolLit, Name)):
        return True
    if isinstance(e, Call):
        return e.name == "len" and all(isinstance(a, Name) for a in e.args)
    if isinstance(e, Unary):
        return e.op == "-" and es_aritmetica(e.operand)
    if isinstance(e, Binary):
        return e.op in ARITMETICA and es_aritmetica(e.left) and es_aritmetica(e.right)
    return False


def es_cota(e: Expr) -> bool:
    if isinstance(e, Binary) and e.op in ("and", "or"):
        return es_cota(e.left) and es_cota(e.right)
    if isinstance(e, Unary) and e.op == "not":
        return es_cota(e.operand)
    if isinstance(e, Binary) and e.op in COMPARACIONES:
        return es_aritmetica(e.left) and es_aritmetica(e.right)
    return False


def solo_cotas(fn: Fn) -> bool:
    return all(es_cota(c) for c in fn.ensures)


def llamadas(e: Expr, acc: set[str] | None = None) -> set[str]:
    """Nombres de función llamados dentro de una expresión (para ver helpers en ensures)."""
    from sello.nodes import children
    acc = set() if acc is None else acc
    if isinstance(e, Call):
        acc.add(e.name)
    for c in children(e):
        llamadas(c, acc)
    return acc


# ---------- ensures cambiado tras E201 ----------

def ensures_de(code: str, nombre: str) -> list[str] | None:
    try:
        prog = parse(code)
    except Exception:
        return None
    for fn in prog.fns:
        if fn.name == nombre:
            return [unparse(c) for c in fn.ensures]
    return None


def cambios_tras_e201(row: dict) -> list[dict]:
    out = []
    intentos = row.get("detail", [])
    for a, b in zip(intentos, intentos[1:]):
        if a.get("sello_error") != "E201":
            continue
        m = re.search(r'"function":\s*"(\w+)"', a.get("feedback", ""))
        if not m:
            continue
        antes, despues = ensures_de(a["code"], m.group(1)), ensures_de(b["code"], m.group(1))
        out.append({"fn": m.group(1), "intento": a["n"], "antes": antes, "despues": despues,
                    "cambiado": antes != despues})
    return out


# ---------- informe ----------

def main() -> int:
    files = [Path(f) for f in sys.argv[1:]]
    if not files:
        print(__doc__); return 2
    for f in files:
        rows = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
        rows = [r for r in rows if r["cond"] == "sello"]
        print(f"\n## {f.name}\n")
        print("| problema | ensures principal | clase | helpers en ensures |")
        print("|---|---|---|---|")
        n_cotas = n_total = 0
        for r in sorted(rows, key=lambda r: r["problem"]):
            if not r.get("code"):
                print(f"| {r['problem']} | (no entregado) | - | - |"); continue
            prog = parse(r["code"])
            fn = next((x for x in prog.fns if x.name == r["problem"]), None)
            if fn is None:
                print(f"| {r['problem']} | (sin función principal) | - | - |"); continue
            n_total += 1
            cl = "cotas" if solo_cotas(fn) else "contenido"
            n_cotas += cl == "cotas"
            propios = {x.name for x in prog.fns}
            helpers = sorted(set().union(*(llamadas(c) for c in fn.ensures)) & propios) if fn.ensures else []
            ens = " · ".join(unparse(c) for c in fn.ensures).replace("|", "\\|")
            print(f"| {r['problem']} | `{ens}` | {cl} | {', '.join(helpers) or '-'} |")
        print(f"\n**Solo cotas: {n_cotas}/{n_total}**\n")
        cambios = [(r["problem"], c) for r in rows for c in cambios_tras_e201(r)]
        if cambios:
            print("Tras un E201:")
            for p, c in cambios:
                print(f"- {p} · `{c['fn']}` intento {c['intento']}: "
                      f"{'ensures cambiado' if c['cambiado'] else 'ensures intacto'} "
                      f"({c['antes']} -> {c['despues']})")
        else:
            print("Ningún E201 seguido de otro intento.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
