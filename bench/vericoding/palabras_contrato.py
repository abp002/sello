#!/usr/bin/env python3
"""ALE-168: métricas prerregistradas de corridas de harness4 (jsonl).

M1: intentos rechazados por una palabra de contrato en un cuerpo (E401 «is only valid inside
`requires` and `ensures`»); M1i, los de `[i]` y `len`. M2: probadas (nivel 2). M3: media de
intentos hasta aceptar (nivel 1). Separa los E401 de índice del primer intento (el `fix` no puede
evitarlos: llega después de fallar) de los repetidos en la misma tarea (los que sí puede).

    uv run python bench/vericoding/palabras_contrato.py bench/resultados/*ale168*.jsonl
"""

import json
import re
import sys
from collections import Counter

PALABRA = re.compile(r"`([^`]+)` is only valid inside `requires` and `ensures`")


def palabra(a: dict) -> str | None:
    if a.get("sello_error") != "E401":
        return None
    m = PALABRA.search(a.get("feedback") or "")
    return m.group(1) if m else None


def metricas(path: str) -> dict:
    filas = [r for r in map(json.loads, open(path)) if r and not r.get("sin_respuesta")]
    por_palabra: Counter = Counter()
    primero = repetido = 0
    for r in filas:
        visto = False
        for a in r["detail"]:
            p = palabra(a)
            if p:
                por_palabra[p] += 1
            if p in ("[i]", "len"):
                primero += a["n"] == 1
                repetido += visto
                visto = True
    acc = [r["accepted_at"] for r in filas if r["accepted_at"]]
    return {"tareas": len(filas), "M1": sum(por_palabra.values()),
            "M1i": por_palabra["[i]"] + por_palabra["len"], "por_palabra": dict(por_palabra),
            "M1i_primer_intento": primero, "M1i_repetido": repetido,
            "M2": sum(1 for r in filas if r["proven_at"]),
            "M3": round(sum(acc) / len(acc), 2) if acc else None, "aceptadas": len(acc),
            "USD": round(sum(r["cost"] for r in filas), 2)}


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(p.rsplit("/", 1)[-1], json.dumps(metricas(p), ensure_ascii=False))
