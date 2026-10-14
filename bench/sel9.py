#!/usr/bin/env python3
"""El análisis prerregistrado del experimento decisivo (SEL-9). Sin modelo.

Lee lo que deja `medir-sel9.sh` en `resultados/` (por etiqueta `sel9-<brazo>-<rep>`) y escribe la
tabla de la nota 'Sello frente a Python con el contrato escrito aparte', con la regla de decisión
aplicada tal como está escrita allí. Brazos: S (Sello), A (Sello con el aviso de ambigüedad al
escribir el contrato, SEL-14), P (Python con CrossHair). Repeticiones: a, b.

    SELLO_BATERIA=nuevas .venv/bin/python bench/sel9.py
"""

from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
R = AQUI / "resultados"
BRAZOS = ("S", "A", "P")
REPS = ("a", "b")


def fichero(prefijo: str, etiqueta: str) -> Path | None:
    xs = sorted(glob.glob(str(R / f"{prefijo}-*-{etiqueta}.jsonl")))
    return Path(xs[-1]) if xs else None


def filas(p: Path | None) -> list[dict]:
    return [json.loads(x) for x in p.read_text().splitlines()] if p else []


def unicidad(contratos: list[dict]) -> dict:
    """Cuántos contratos de Sello finales fijan la respuesta (`sello.unique`, sin cuerpo)."""
    from sello.compile import compile_source
    from sello.errors import SelloError
    from sello.unique import unique_program
    c = {"unique": 0, "ambiguous": 0, "unknown": 0}
    for r in contratos:
        if not r.get("compila"):
            continue
        try:
            program, _ = compile_source(r["code"])
        except SelloError:
            continue
        c[unique_program(program, {r["problem"]})[r["problem"]].status] += 1
    return c


def medir(brazo: str, rep: str) -> dict | None:
    et = f"sel9-{brazo}-{rep}"
    contratos, cuerpos = filas(fichero("contratos", et)), filas(fichero("juez", et))
    if not cuerpos:
        return None
    lit = filas(fichero("literales", et))
    mut = filas(fichero("mutantes", et))
    ent = [r for r in cuerpos if r.get("accepted_at")]
    o = [r["oracle"] for r in ent]
    rec = [m["recuento"] for m in mut if not m.get("descartada")]
    lm = [f["medida"] for f in lit if f.get("medida")]
    d = {
        "entregadas": len(ent), "tareas": len(cuerpos),
        "sil_llamadas": sum(x.get("dom_silencioso", 0) for x in o),
        "sil_tareas": sum(x.get("dom_silencioso", 0) > 0 for x in o),
        "ruidosos": sum(x.get("dom_ruidoso", 0) for x in o),
        "cazados": sum(x.get("cazados", 0) for x in o),
        "intentos": sum(r["accepted_at"] for r in ent) / max(1, len(ent)),
        "usd": sum(r["cost"] for r in contratos) + sum(r["cost"] for r in cuerpos),
        "contratos_compilan": sum(bool(r.get("compila")) for r in contratos),
        "avisos": sum(bool(r.get("avisado")) for r in contratos),
        "admite_incorrecto": (sum(m["admite_incorrecto"] for m in lm), sum(m["incorrectos"] for m in lm)),
        "flojos": sum(m["incorrectos"] and m["admite_incorrecto"] / m["incorrectos"] >= 0.6 for m in lm),
        "rechazan_correcto": sum(m["rechaza_correcto"] > 0 for m in lm),
        "mut_llegan": sum(k["llegan"] for k in rec), "mut_sil": sum(k["silencioso"] for k in rec),
        "mut_caz": sum(k["cazado"] for k in rec), "mut_gen": sum(k["generados"] for k in rec),
    }
    if brazo != "P":
        d["unicidad"] = unicidad(contratos)
    return d


def pct(a: int, b: int) -> str:
    return f"{100 * a / b:.0f} %" if b else "-"


def main() -> int:
    m = {(b, r): medir(b, r) for b in BRAZOS for r in REPS}
    cols = [(b, r) for b in BRAZOS for r in REPS if m[(b, r)]]
    out = ["# Experimento decisivo (SEL-9)", "",
           "Prerregistrado en el vault: 'Sello frente a Python con el contrato escrito aparte'.", "",
           "| | " + " | ".join(f"{b}·{r}" for b, r in cols) + " |", "|---|" + "---|" * len(cols)]

    def fila(nombre, f):
        out.append(f"| {nombre} | " + " | ".join(f(m[c]) for c in cols) + " |")
    fila("entregadas", lambda d: f"{d['entregadas']}/{d['tareas']}")
    fila("**silenciosos en el dominio (llamadas)**", lambda d: f"**{d['sil_llamadas']}**")
    fila("**tareas con algún silencioso**", lambda d: f"**{d['sil_tareas']}**")
    fila("ruidosos en el dominio (llamadas)", lambda d: str(d["ruidosos"]))
    fila("cazados por el contrato (llamadas)", lambda d: str(d["cazados"]))
    fila("intentos hasta aceptar (cuerpo)", lambda d: f"{d['intentos']:.2f}")
    fila("coste USD (contrato + cuerpo)", lambda d: f"{d['usd']:.2f}")
    fila("contratos que compilan", lambda d: str(d["contratos_compilan"]))
    fila("contratos que admiten lo incorrecto (casos)", lambda d: pct(*d["admite_incorrecto"]))
    fila("contratos flojos (≥ 60 %)", lambda d: str(d["flojos"]))
    fila("contratos que rechazan lo correcto", lambda d: str(d["rechazan_correcto"]))
    fila("mutantes: silenciosos / llegan", lambda d: f"{d['mut_sil']}/{d['mut_llegan']}")
    fila("mutantes: cazados / llegan", lambda d: f"{d['mut_caz']}/{d['mut_llegan']}")
    fila("mutantes: silenciosos / generados", lambda d: pct(d["mut_sil"], d["mut_gen"]))
    fila("avisos de ambigüedad", lambda d: str(d["avisos"]) if d.get("unicidad") is not None else "-")
    fila("contratos finales unique / ambiguous / unknown",
         lambda d: "{unique}/{ambiguous}/{unknown}".format(**d["unicidad"]) if d.get("unicidad") else "-")

    # La regla, tal como está escrita en la nota.
    def sil(b): return [m[(b, r)]["sil_llamadas"] for r in REPS if m[(b, r)]]
    def ruido(b): xs = sil(b); return abs(xs[0] - xs[1]) if len(xs) == 2 else None
    out += ["", "## Regla de decisión", ""]
    if all(len(sil(b)) == 2 for b in ("S", "P")):
        s, p, ns, np_ = sil("S"), sil("P"), ruido("S"), ruido("P")
        margen = max(ns, np_)
        dif = [x - y for x, y in zip(s, p)]
        if all(d_ < 0 for d_ in dif) and all(-d_ > margen for d_ in dif):
            v = "GANA SELLO"
        elif all(d_ > 0 for d_ in dif) and all(d_ > margen for d_ in dif):
            v = "GANA PYTHON"
        else:
            v = "EMPATE (dentro del ruido)"
        out.append(f"- Silenciosos en el dominio, S − P por repetición: {dif}; ruido entre repeticiones: "
                   f"S {ns}, P {np_}. **{v}**.")
        cs = [m[('S', r)]['usd'] for r in REPS]; cp_ = [m[('P', r)]['usd'] for r in REPS]
        out.append(f"- Coste: S {sum(cs):.2f} USD frente a P {sum(cp_):.2f} USD "
                   f"({sum(cs) / max(sum(cp_), 1e-9):.1f}×; si Sello gana con más de 2×, la regla no le da la victoria).")
    if all(len(sil(b)) == 2 for b in ("S", "A")):
        a_, s = sil("A"), sil("S")
        ra = [m[("A", r)]["ruidosos"] for r in REPS]; rs = [m[("S", r)]["ruidosos"] for r in REPS]
        ai = [m[("A", r)]["admite_incorrecto"][0] for r in REPS]; si = [m[("S", r)]["admite_incorrecto"][0] for r in REPS]
        entra = all(x <= y for x, y in zip(a_, s)) and sum(ai) < sum(si) and sum(ra) <= sum(rs)
        out.append(f"- Aviso (A frente a S): silenciosos {a_} frente a {s}; admite lo incorrecto {ai} frente a "
                   f"{si}; ruidosos {ra} frente a {rs}. **{'ENTRA' if entra else 'NO ENTRA'}**.")
    md = "\n".join(out) + "\n"
    (R / "sel9.md").write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
