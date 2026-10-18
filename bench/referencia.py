#!/usr/bin/env python3
"""El análisis prerregistrado del issue #6: ¿cierra la guía del helper de referencia los contratos de
las tareas definidas por un proceso? Sin modelo. Nota del vault: 'El helper de referencia cierra los
contratos de las tareas definidas por un proceso'.

Brazo U: el brazo T del issue #5 repetido con la spec que guía el helper de referencia (haiku,
contrato propio, sin aviso; etiquetas `n3-U-<rep>`, de `medir-referencia.sh`). Se compara con T y se
pone P al lado.

    SELLO_BATERIA=n3 .venv/bin/python bench/referencia.py
"""

from __future__ import annotations

import re
import sys

from sel9 import R, REPS, fichero, filas

import cuenta

RESERVADAS = {"len", "count", "contains", "distinct", "sorted"}


def fija_a_helper(code: str, fn: str) -> bool:
    """¿Algún `ensures` de la principal dice `result == h(...)` con `h` una función del programa?"""
    m = re.search(rf"^fn {re.escape(fn)}\(.*?^\{{", code, re.S | re.M)
    if not m:
        return False
    propias = set(re.findall(r"^fn (\w+)\(", code, re.M)) - {fn}
    for linea in m.group(0).splitlines():
        linea = linea.strip()
        if linea.startswith("ensures"):
            for h in re.findall(r"\bresult\s*==\s*\(?\s*(\w+)\(", linea):
                if h in propias and h not in RESERVADAS:
                    return True
    return False


def medir(brazo: str, rep: str) -> dict | None:
    d = cuenta.medir(brazo, rep)
    if d is None:
        return None
    ent = [r for r in filas(fichero("juez", f"n3-{brazo}-{rep}")) if r.get("accepted_at")]
    d["referencia"] = sum(fija_a_helper(r["code"], r["problem"]) for r in ent) if brazo != "P" else 0
    return d


def main() -> int:
    m = {(b, r): medir(b, r) for b in ("T", "U", "P") for r in REPS}
    cols = [c for c in m if m[c]]
    out = ["# El helper de referencia (issue #6)", "",
           "Prerregistrado en el vault: 'El helper de referencia cierra los contratos de las tareas "
           "definidas por un proceso'. U es T con la spec que guía el helper de referencia.", "",
           "| | " + " | ".join(f"{b}·{r}" for b, r in cols) + " |", "|---|" + "---|" * len(cols)]

    def fila(nombre, f):
        out.append(f"| {nombre} | " + " | ".join(f(m[c]) for c in cols) + " |")
    fila("entregadas", lambda d: f"{d['entregadas']}/{d['tareas']}")
    fila("principales con `ensures result == helper(...)`", lambda d: str(d["referencia"]))
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
    if not all(m[(b, r)] for b in ("T", "U") for r in REPS):
        out.append("- Faltan brazos: sin veredicto.")
    else:
        def serie(b, k): return [m[(b, r)][k] for r in REPS]
        adm_t, adm_u = serie("T", "admite"), serie("U", "admite")
        margen = max(abs(adm_t[0] - adm_t[1]), abs(adm_u[0] - adm_u[1]))
        c1 = sum(adm_u) < sum(adm_t) - margen
        c2 = sum(serie("U", "silencio")) <= sum(serie("T", "silencio"))
        c3 = sum(serie("U", "ruidosos")) <= sum(serie("T", "ruidosos"))
        n2t, n2u = [x[0] for x in serie("T", "nivel2")], [x[0] for x in serie("U", "nivel2")]
        margen2 = max(abs(n2t[0] - n2t[1]), abs(n2u[0] - n2u[1]))
        c4 = sum(n2u) >= sum(n2t) - margen2
        ok = lambda c: "sí" if c else "no"
        out += [f"1. Casos incorrectos admitidos, T {adm_t} frente a U {adm_u}, margen {margen}: {ok(c1)}.",
                f"2. Silencio, T {serie('T', 'silencio')} frente a U {serie('U', 'silencio')}: {ok(c2)}.",
                f"3. Ruidosos, T {serie('T', 'ruidosos')} frente a U {serie('U', 'ruidosos')}: {ok(c3)}.",
                f"4. Nivel ≥ 2, T {n2t} frente a U {n2u}, margen {margen2}: {ok(c4)}.",
                "", f"**{'ENTRA' if c1 and c2 and c3 and c4 else 'NO ENTRA'}**."]
    md = "\n".join(out) + "\n"
    (R / "referencia.md").write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
