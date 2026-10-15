#!/usr/bin/env python3
"""El análisis prerregistrado del issue #3: ¿aportan los niveles 2 y 3 de Sello sobre contratos de
Python? Sin modelo. Nota del vault: 'Los niveles 2 y 3 frente a CrossHair con el contrato propio'.

Lee lo que deja `medir-n3.sh` (etiquetas `n3-<brazo>-<rep>`). Haiku escribe contrato y cuerpo a la
vez, como en el uso real. Brazos: S (`sello`), A (`sello` + aviso con `sello.unique`), P
(`python_propio`, CrossHair en el juez débil), Q (`python_propio` + aviso con CrossHair,
`contrato_py.ambiguo`). Repeticiones: a, b.

    SELLO_BATERIA=n3 .venv/bin/python bench/n3.py
"""

from __future__ import annotations

import sys

from sel9 import R, REPS, fichero, filas

import contrato_py as cp

BRAZOS = ("S", "A", "P", "Q")
MATERIAL = 4  # avisos mínimos (de 72 soluciones por lenguaje) para que el nivel 3 tenga algo que hacer


def ambiguo(r: dict) -> str:
    """unique | ambiguous | unknown del contrato de una solución entregada. En Python solo hay
    ambiguous (con testigo confirmado) o unknown: CrossHair busca, no prueba."""
    if r["cond"] == "python_propio":
        return "ambiguous" if cp.ambiguo(r["code"], r["problem"]) else "unknown"
    from sello.compile import compile_source
    from sello.errors import SelloError
    from sello.unique import unique_program
    try:
        program, _ = compile_source(r["code"])
    except SelloError:
        return "unknown"
    return unique_program(program, {r["problem"]})[r["problem"]].status


def nivel2(r: dict) -> bool:
    """¿La principal de Sello entregada tiene nivel ≥ 2?"""
    from sello.compile import check_source
    from sello.errors import SelloError
    try:
        out = check_source(r["code"])
    except SelloError:
        return False
    return any(f["name"] == r["problem"] and f.get("level", 0) >= 2 for f in out["functions"])


def medir(brazo: str, rep: str) -> dict | None:
    et = f"n3-{brazo}-{rep}"
    cuerpos = filas(fichero("juez", et))
    if not cuerpos:
        return None
    lm = [f["medida"] for f in filas(fichero("literales", et)) if f.get("medida")]
    rec = [x["recuento"] for x in filas(fichero("mutantes", et)) if not x.get("descartada")]
    ent = [r for r in cuerpos if r.get("accepted_at")]
    o = [r["oracle"] for r in ent]
    estados = [ambiguo(r) for r in ent]
    d = {
        "entregadas": len(ent), "tareas": len(cuerpos),
        "avisos": sum(bool(r.get("avisado")) for r in cuerpos),
        "sustituye": sum(r.get("aviso_sustituye") is True for r in cuerpos),
        "u": estados.count("unique"), "a": estados.count("ambiguous"), "k": estados.count("unknown"),
        "sil_llamadas": sum(x.get("dom_silencioso", 0) for x in o),
        "ruidosos": sum(x.get("dom_ruidoso", 0) for x in o),
        "cazados": sum(x.get("cazados", 0) for x in o),
        "intentos": sum(r["accepted_at"] for r in ent) / max(1, len(ent)),
        "usd": sum(r["cost"] for r in cuerpos),
        "admite": sum(m["admite_incorrecto"] for m in lm), "incorrectos": sum(m["incorrectos"] for m in lm),
        "flojos": sum(m["incorrectos"] and m["admite_incorrecto"] / m["incorrectos"] >= 0.6 for m in lm),
        "rechazan_correcto": sum(m["rechaza_correcto"] > 0 for m in lm),
        "mut_gen": sum(k["generados"] for k in rec), "mut_llegan": sum(k["llegan"] for k in rec),
        "mut_sil": sum(k["silencioso"] for k in rec), "mut_caz": sum(k["cazado"] for k in rec),
        "mut_prover": sum(k["muerto_probador"] for k in rec),
    }
    d["silencio"] = d["sil_llamadas"] + d["mut_sil"]
    d["escapes"] = d["mut_caz"]  # violan el contrato (cazados en producción) tras pasar el verificador estático
    if brazo in ("S", "A"):
        d["nivel2"] = (sum(nivel2(r) for r in ent), len(ent))
    return d


def main() -> int:
    m = {(b, r): medir(b, r) for b in BRAZOS for r in REPS}
    cols = [(b, r) for b in BRAZOS for r in REPS if m[(b, r)]]
    out = ["# Los niveles 2 y 3 frente a CrossHair (issue #3)", "",
           "Prerregistrado en el vault: 'Los niveles 2 y 3 frente a CrossHair con el contrato propio'.", "",
           "| | " + " | ".join(f"{b}·{r}" for b, r in cols) + " |", "|---|" + "---|" * len(cols)]

    def fila(nombre, f):
        out.append(f"| {nombre} | " + " | ".join(f(m[c]) for c in cols) + " |")
    fila("entregadas", lambda d: f"{d['entregadas']}/{d['tareas']}")
    fila("avisos de ambigüedad (sustituyen)", lambda d: f"{d['avisos']} ({d['sustituye']})")
    fila("contratos entregados unique / ambiguous / unknown", lambda d: f"{d['u']}/{d['a']}/{d['k']}")
    fila("**contratos que admiten lo incorrecto (casos)**", lambda d: f"**{d['admite']}/{d['incorrectos']}**")
    fila("contratos flojos (≥ 60 %)", lambda d: str(d["flojos"]))
    fila("contratos que rechazan lo correcto", lambda d: str(d["rechazan_correcto"]))
    fila("**silenciosos: llamadas del dominio + mutantes**", lambda d: f"**{d['sil_llamadas']} + {d['mut_sil']}**")
    fila("ruidosos en el dominio (llamadas)", lambda d: str(d["ruidosos"]))
    fila("cazados por el contrato (llamadas)", lambda d: str(d["cazados"]))
    fila("**escapes: mutantes que violan el contrato y llegan**", lambda d: f"**{d['escapes']}**")
    fila("mutantes muertos por el verificador estático", lambda d: str(d["mut_prover"]))
    fila("mutantes: llegan / generados", lambda d: f"{d['mut_llegan']}/{d['mut_gen']}")
    fila("principales entregadas con nivel ≥ 2", lambda d: f"{d['nivel2'][0]}/{d['nivel2'][1]}" if d.get("nivel2") else "-")
    fila("intentos hasta aceptar", lambda d: f"{d['intentos']:.2f}")
    fila("coste USD", lambda d: f"{d['usd']:.2f}")

    out += ["", "## Reglas", ""]
    if not all(m[(b, r)] for b in BRAZOS for r in REPS):
        out.append("- Faltan brazos: sin veredicto.")
    else:
        def serie(b, k): return [m[(b, r)][k] for r in REPS]
        for base, av, lang in (("S", "A", "Sello"), ("P", "Q", "Python")):
            avisos = sum(serie(av, "avisos"))
            if avisos < MATERIAL:
                v = f"SIN MATERIAL ({avisos} avisos de {sum(serie(av, 'tareas'))} soluciones)"
            else:
                sil_ok = all(x <= y for x, y in zip(serie(av, "silencio"), serie(base, "silencio")))
                ai, bi = sum(serie(av, "admite")), sum(serie(base, "admite"))
                ra, rb = sum(serie(av, "ruidosos")), sum(serie(base, "ruidosos"))
                v = ("ENTRA" if sil_ok and ai < bi and ra <= rb else "NO ENTRA") + \
                    (f" (silencio {serie(av, 'silencio')} frente a {serie(base, 'silencio')}; admite lo "
                     f"incorrecto {ai} frente a {bi}; ruidosos {ra} frente a {rb})")
            out.append(f"- Nivel 3 en {lang} ({av} frente a {base}), {avisos} avisos: **{v}**.")
        s, p = serie("S", "escapes"), serie("P", "escapes")
        margen = max(abs(s[0] - s[1]), abs(p[0] - p[1]))
        dif = [x - y for x, y in zip(s, p)]
        v = "GANA SELLO" if all(-x > margen for x in dif) else "GANA PYTHON" if all(x > margen for x in dif) else "EMPATE"
        out.append(f"- Nivel 2 (escapes, S − P por repetición: {dif}; margen {margen}): **{v}**.")
    md = "\n".join(out) + "\n"
    (R / "n3.md").write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
