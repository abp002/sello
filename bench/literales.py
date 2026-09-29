#!/usr/bin/env python3
"""La prueba de literales: un contrato es un juez, y se mide como un juez, sin cuerpo por medio.

Pregunta 1 de 'El contrato se puede escribir sin el cuerpo' (vault). Por cada llamada de
dominio del oráculo, la principal pasa a tener por cuerpo el literal de la respuesta correcta y
se llama con ese caso: si su contrato la rechaza, el contrato **rechaza lo correcto**. Y otra vez
con el literal de una respuesta incorrecta, la del caso siguiente del oráculo, ciclando (si
coincide con la correcta, el caso se salta): si nada salta, el contrato **admite lo incorrecto**.
Solo se ejecuta: ni probador ni ejemplos de la principal, que fallarían contra un cuerpo
constante. Los ejemplos de los helpers sí corren.

Lo prerregistrado es el E201 del `ensures`. El E300 (un `requires` que deja fuera una entrada
del dominio) se cuenta aparte. La zona ambigua no cuenta (regla 3): se apunta cuántas rechaza.

    uv run python bench/literales.py bench/resultados/contratos-<fecha>-sonnet.jsonl \\
        bench/resultados/juez-2026-09-05-0015-sonnet.jsonl
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from dataclasses import dataclass, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import RESULTADOS, sello_lit  # noqa: E402
from harness3 import PROBLEMAS, cargar_contratos, llamada  # noqa: E402
import contrato as ct  # noqa: E402
from cotas import solo_cotas  # noqa: E402

from sello.checker import Checker  # noqa: E402
from sello.compile import run_examples  # noqa: E402
from sello.errors import SelloError  # noqa: E402
from sello.interp import Interpreter  # noqa: E402
from sello.nodes import Program  # noqa: E402
from sello.parser import parse_expr  # noqa: E402

ADMITE, E201, E300, OTRO = "admite", "E201", "E300", "otro"
FUEL = 5_000_000  # un helper que no termina con una entrada del oráculo no cuelga la medición


@dataclass
class Veredicto:
    que: str                       # admite | E201 | E300 | otro
    error: dict | None = None      # el error tal como lo ve un modelo


def veredicto(c: ct.Contrato, p: dict, args: list, valor: object) -> Veredicto:
    """Qué dice el contrato `c` de `valor` como respuesta a la llamada con `args`. Si el propio
    contrato no se sostiene (un helper que no tipa o falla sus ejemplos), se lanza."""
    principal = replace(c.principal, body=parse_expr(sello_lit(valor)))
    program = Program([*c.helpers, principal])
    Checker(program).check()
    interp = Interpreter(program)
    run_examples(Program(c.helpers), interp)
    interp.fuel = FUEL
    try:
        interp.eval(parse_expr(llamada(p, args)), {}, None)
    except SelloError as e:
        return Veredicto(e.code if e.code in (E201, E300) else OTRO, e.to_dict())
    except RecursionError:
        return Veredicto(OTRO, {"code": "E500", "what": "recursion too deep"})
    return Veredicto(ADMITE)


def medir(c: ct.Contrato, p: dict) -> dict:
    """Los recuentos de un contrato sobre el oráculo de su problema."""
    oraculo = p["oracle"]
    dom = [(i, x) for i, x in enumerate(oraculo) if x["zone"] == "domain"]
    correctos = [veredicto(c, p, x["args"], x["expect"]).que for _, x in dom]
    incorrectos = []
    for i, x in dom:
        otro = oraculo[(i + 1) % len(oraculo)]["expect"]
        if otro != x["expect"]:
            incorrectos.append(veredicto(c, p, x["args"], otro).que)
    ambiguos = [veredicto(c, p, x["args"], x["expect"]).que for x in oraculo if x["zone"] == "ambiguous"]
    return {"dominio": len(dom), "rechaza_correcto": correctos.count(E201),
            "requires_fuera": correctos.count(E300), "otros": correctos.count(OTRO),
            "incorrectos": len(incorrectos), "admite_incorrecto": incorrectos.count(ADMITE),
            "ambiguos": len(ambiguos), "ambiguos_rechazados": sum(v != ADMITE for v in ambiguos),
            "solo_cotas": solo_cotas(c.principal)}


def pct(a: int, b: int) -> str:
    return f"{100 * a / b:.0f} %" if b else "-"


def resumen(filas: list[dict], when: str) -> str:
    fuentes = list(dict.fromkeys(f["origen"] for f in filas))
    out = [f"# Prueba de literales {when}", "",
           "Por problema: rechaza lo correcto (E201, de 25) · `requires` fuera (E300) · admite lo "
           "incorrecto (de los casos válidos). `-`: sin contrato que compile. Prerregistrado en el "
           "vault: 'El contrato se puede escribir sin el cuerpo'.", "",
           "| Problema | " + " | ".join(fuentes) + " |", "|---|" + "---|" * len(fuentes)]
    by = {(f["problem"], f["origen"]): f for f in filas}
    for pr in sorted({f["problem"] for f in filas}):
        celdas = []
        for fu in fuentes:
            f = by.get((pr, fu))
            if f is None or f.get("medida") is None:
                celdas.append("-")
            else:
                m = f["medida"]
                celdas.append(f"{m['rechaza_correcto']} · {m['requires_fuera']} · "
                              f"{m['admite_incorrecto']}/{m['incorrectos']}" + (" · cotas" if m["solo_cotas"] else ""))
        out.append(f"| {pr} | " + " | ".join(celdas) + " |")

    def ms(fu): return [f["medida"] for f in filas if f["origen"] == fu and f.get("medida")]
    def stat(nombre, g): out.append(f"| {nombre} | " + " | ".join(g(fu) for fu in fuentes) + " |")
    out += ["", "| | " + " | ".join(fuentes) + " |", "|---|" + "---|" * len(fuentes)]
    stat("contratos que compilan", lambda fu: f"{len(ms(fu))}/{sum(f['origen'] == fu for f in filas)}")
    stat("**rechazan lo correcto** (algún E201)", lambda fu: f"**{sum(m['rechaza_correcto'] > 0 for m in ms(fu))}**")
    stat("casos correctos rechazados (E201)", lambda fu: str(sum(m["rechaza_correcto"] for m in ms(fu))))
    stat("contratos con `requires` fuera del dominio (E300)", lambda fu: str(sum(m["requires_fuera"] > 0 for m in ms(fu))))
    stat("admiten lo incorrecto (casos)", lambda fu: pct(sum(m["admite_incorrecto"] for m in ms(fu)),
                                                          sum(m["incorrectos"] for m in ms(fu))))
    stat("**flojos** (admiten el 60 % o más)", lambda fu: f"**{sum(m['incorrectos'] and m['admite_incorrecto'] / m['incorrectos'] >= 0.6 for m in ms(fu))}**")
    stat("solo cotas (forma, `cotas.py`)", lambda fu: str(sum(m["solo_cotas"] for m in ms(fu))))
    stat("ambiguas rechazadas (declarado)", lambda fu: f"{sum(m['ambiguos_rechazados'] for m in ms(fu))}/{sum(m['ambiguos'] for m in ms(fu))}")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("jsonl", nargs="+", type=Path, help="corridas de contratar.py o del juez")
    args = ap.parse_args()
    probs = {p["fn"]: p for p in (json.loads(f.read_text()) for f in sorted(PROBLEMAS.glob("*.json")))}
    filas = []
    for path in args.jsonl:
        contratos = cargar_contratos(path)
        for fn, p in probs.items():
            fila = {"problem": fn, "origen": path.name, "medida": None}
            if fn in contratos:
                try:
                    fila["medida"] = medir(ct.extraer(contratos[fn]["code"], fn), p)
                except SelloError as e:
                    fila["error"] = e.to_dict()
            filas.append(fila)
    when = dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    base = RESULTADOS / f"literales-{when}"
    base.with_suffix(".jsonl").write_text("".join(json.dumps(f, ensure_ascii=False) + "\n" for f in filas))
    md = resumen(filas, when)
    base.with_suffix(".md").write_text(md)
    print(md)
    print(f"detalle: {base.with_suffix('.jsonl')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
