#!/usr/bin/env python3
"""El análisis prerregistrado del issue #5: ¿cierran `count` y `sum` con condición los contratos de
cotas? Sin modelo. Nota del vault: 'Contar y sumar con condición cierra los contratos de cotas'.

Brazo T (S′): el brazo S del issue #3 repetido con la spec que trae `count` y `sum` (haiku, contrato
propio, sin aviso; etiquetas `n3-T-<rep>`, de `medir-cuenta.sh`). Se compara con S de entonces y
se pone P al lado.

    SELLO_BATERIA=n3 .venv/bin/python bench/cuenta.py
"""

from __future__ import annotations

import re
import sys

from sel9 import R, REPS, fichero, filas

import n3

FORMA = re.compile(r"\b(count|sum)\s+\w+\s+in\b")


def medir(brazo: str, rep: str) -> dict | None:
    d = n3.medir(brazo, rep)
    if d is None:
        return None
    ent = [r for r in filas(fichero("juez", f"n3-{brazo}-{rep}")) if r.get("accepted_at")]
    if "nivel2" not in d and brazo != "P":
        d["nivel2"] = (sum(n3.nivel2(r) for r in ent), len(ent))
    d["usan"] = sum(bool(FORMA.search(r["code"])) for r in ent)
    return d


def main() -> int:
    m = {(b, r): medir(b, r) for b in ("S", "T", "P") for r in REPS}
    cols = [c for c in m if m[c]]
    out = ["# Contar y sumar con condición (issue #5)", "",
           "Prerregistrado en el vault: 'Contar y sumar con condición cierra los contratos de cotas'. "
           "T es S′: el brazo S del issue #3 con la spec nueva.", "",
           "| | " + " | ".join(f"{b}·{r}" for b, r in cols) + " |", "|---|" + "---|" * len(cols)]

    def fila(nombre, f):
        out.append(f"| {nombre} | " + " | ".join(f(m[c]) for c in cols) + " |")
    fila("entregadas", lambda d: f"{d['entregadas']}/{d['tareas']}")
    fila("contratos que usan `count` o `sum`", lambda d: str(d["usan"]))
    fila("**casos incorrectos que admite el contrato**", lambda d: f"**{d['admite']}/{d['incorrectos']}**")
    fila("contratos flojos (≥ 60 %)", lambda d: str(d["flojos"]))
    fila("contratos que rechazan lo correcto", lambda d: str(d["rechazan_correcto"]))
    fila("**silencio: dominio + mutantes**", lambda d: f"**{d['sil_llamadas']} + {d['mut_sil']}**")
    fila("ruidosos en el dominio", lambda d: str(d["ruidosos"]))
    fila("escapes", lambda d: str(d["escapes"]))
    fila("principales con nivel ≥ 2", lambda d: f"{d['nivel2'][0]}/{d['nivel2'][1]}" if d.get("nivel2") else "-")
    fila("contratos unique / ambiguous / unknown", lambda d: f"{d['u']}/{d['a']}/{d['k']}")
    fila("intentos hasta aceptar", lambda d: f"{d['intentos']:.2f}")
    fila("coste USD", lambda d: f"{d['usd']:.2f}")

    out += ["", "## Regla", ""]
    if not all(m[(b, r)] for b in ("S", "T") for r in REPS):
        out.append("- Faltan brazos: sin veredicto.")
    else:
        def serie(b, k): return [m[(b, r)][k] for r in REPS]
        adm_s, adm_t = serie("S", "admite"), serie("T", "admite")
        margen = max(abs(adm_s[0] - adm_s[1]), abs(adm_t[0] - adm_t[1]))
        c1 = all(s - t > margen for s, t in zip(adm_s, adm_t))
        c2 = sum(serie("T", "silencio")) <= sum(serie("S", "silencio"))
        c3 = sum(serie("T", "ruidosos")) <= sum(serie("S", "ruidosos"))
        n2s, n2t = [x[0] for x in serie("S", "nivel2")], [x[0] for x in serie("T", "nivel2")]
        margen2 = max(abs(n2s[0] - n2s[1]), abs(n2t[0] - n2t[1]))
        c4 = sum(n2t) >= sum(n2s) - margen2
        ok = lambda c: "sí" if c else "no"
        out += [f"1. Casos incorrectos admitidos, S {adm_s} frente a T {adm_t}, margen {margen}: {ok(c1)}.",
                f"2. Silencio, S {serie('S', 'silencio')} frente a T {serie('T', 'silencio')}: {ok(c2)}.",
                f"3. Ruidosos, S {serie('S', 'ruidosos')} frente a T {serie('T', 'ruidosos')}: {ok(c3)}.",
                f"4. Nivel ≥ 2, S {n2s} frente a T {n2t}, margen {margen2}: {ok(c4)}.",
                "", f"**{'ENTRA' if c1 and c2 and c3 and c4 else 'NO ENTRA'}**."]
    md = "\n".join(out) + "\n"
    (R / "cuenta.md").write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
