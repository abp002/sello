"""El juez imperfecto: lógica pura de clasificación y resumen. Sin llamadas al modelo.

Una solución aceptada por el juez débil (compilador + ejemplos visibles) se pasa al
oráculo. Cada llamada del oráculo acaba en uno de cuatro resultados:

  correcto     coincide con la referencia
  silencioso   valor distinto sin ninguna señal            <- el error que cuenta
  rechazado    la entrada se rechaza en la frontera        E300/E500 · excepción · timeout
  cazado       resultado incorrecto que el contrato detectó E201 · AssertionError

Y cada caso está en una zona: `domain` (el enunciado lo exige) o `ambiguous` (el enunciado
lo calla). En el dominio todo lo que no es correcto es error. En la zona ambigua, rechazar
o cazar es comportamiento declarado y no penaliza.
"""

from __future__ import annotations

# Lo que devuelve el ejecutor por caso, antes de clasificar.
OK, WRONG, REJECT, CAUGHT = "ok", "wrong", "reject", "caught"

CORRECTO, SILENCIOSO, RUIDOSO, DECLARADO = "correcto", "silencioso", "ruidoso", "declarado"


def resultado_sello(fallo: dict | None) -> str:
    """Traduce una entrada de `failed` de `sello test` (o None si pasó) al resultado bruto."""
    if fallo is None:
        return OK
    err = fallo.get("error")
    if err is None:
        return WRONG
    code = err.get("code", "")
    if code == "E201":
        return CAUGHT
    return REJECT


def resultado_python(status: str) -> str:
    """El driver de Python emite ok | wrong | assert | raise | timeout."""
    return {"ok": OK, "wrong": WRONG, "assert": CAUGHT}.get(status, REJECT)


def clasificar(zona: str, resultado: str) -> str:
    """Zona x resultado bruto -> categoría contable.

    En el dominio, rechazado y cazado son errores ruidosos (el código está mal, pero se
    nota). En la zona ambigua son comportamiento declarado.
    """
    if resultado == OK:
        return CORRECTO
    if resultado == WRONG:
        return SILENCIOSO
    return RUIDOSO if zona == "domain" else DECLARADO


def contar(casos: list[dict]) -> dict:
    """casos: [{"zone", "result", ...}] ya ejecutados. Devuelve los recuentos de un problema."""
    c = {"dom_total": 0, "dom_correcto": 0, "dom_silencioso": 0, "dom_ruidoso": 0,
         "amb_total": 0, "amb_correcto": 0, "amb_silencioso": 0, "amb_declarado": 0,
         "cazados": 0}
    for x in casos:
        cat = clasificar(x["zone"], x["result"])
        pref = "dom" if x["zone"] == "domain" else "amb"
        c[f"{pref}_total"] += 1
        c[f"{pref}_{cat}"] += 1
        if x["result"] == CAUGHT:
            c["cazados"] += 1
    c["silenciosos"] = c["dom_silencioso"] + c["amb_silencioso"]
    return c


def resumen(rows: list[dict], model: str, when: str) -> str:
    """rows: una por (problema, condición) con `accepted_at`, `oracle` (recuentos) y coste."""
    conds = sorted({r["cond"] for r in rows})
    probs = sorted({r["problem"] for r in rows})
    by = {(r["problem"], r["cond"]): r for r in rows}
    out = [f"# Juez imperfecto {when} · modelo `{model}`", "",
           "Errores silenciosos que llegaron a producción tras pasar el juez débil "
           "(`-` = el juez débil no aceptó ninguna solución). Formato: silenciosos "
           "dominio+ambigua · cazados por el contrato.", "",
           "| Problema | " + " | ".join(conds) + " |", "|---|" + "---|" * len(conds)]
    for pr in probs:
        cells = []
        for cd in conds:
            r = by.get((pr, cd))
            if r is None or not r["accepted_at"]:
                cells.append("-")
            else:
                o = r["oracle"]
                cells.append(f"{o['dom_silencioso']}+{o['amb_silencioso']} · {o['cazados']}")
        out.append(f"| {pr} | " + " | ".join(cells) + " |")

    out += ["", "| | " + " | ".join(conds) + " |", "|---|" + "---|" * len(conds)]

    def rs(cd): return [r for r in rows if r["cond"] == cd]
    def acc(cd): return [r for r in rs(cd) if r["accepted_at"]]
    def suma(cd, k): return sum(r["oracle"][k] for r in acc(cd))
    def stat(name, f): out.append(f"| {name} | " + " | ".join(f(cd) for cd in conds) + " |")

    stat("aceptadas por el juez débil", lambda cd: f"{len(acc(cd))}/{len(rs(cd))}")
    stat("media de intentos hasta aceptar", lambda cd: f"{sum(r['accepted_at'] for r in acc(cd)) / max(1, len(acc(cd))):.2f}")
    stat("**silenciosos (total)**", lambda cd: f"**{suma(cd, 'silenciosos')}**")
    stat("silenciosos en el dominio", lambda cd: str(suma(cd, "dom_silencioso")))
    stat("silenciosos en la zona ambigua", lambda cd: str(suma(cd, "amb_silencioso")))
    stat("problemas sin ningún silencioso", lambda cd: f"{sum(1 for r in acc(cd) if r['oracle']['silenciosos'] == 0)}/{len(acc(cd))}")
    stat("ruidosos en el dominio (rechazo indebido)", lambda cd: str(suma(cd, "dom_ruidoso")))
    stat("declarados en la zona ambigua", lambda cd: str(suma(cd, "amb_declarado")))
    stat("cazados por el contrato (E201 / assert)", lambda cd: str(suma(cd, "cazados")))
    stat("llamadas del oráculo", lambda cd: str(suma(cd, "dom_total") + suma(cd, "amb_total")))
    stat("tokens de salida", lambda cd: str(sum(r["tokens_out"] for r in rs(cd))))
    stat("de ellos, razonamiento", lambda cd: str(sum(r.get("thinking", 0) for r in rs(cd))))
    stat("coste USD", lambda cd: f"{sum(r['cost'] for r in rs(cd)):.3f}")
    stat("tiempo total (s)", lambda cd: f"{sum(r['ms'] for r in rs(cd)) / 1000:.0f}")
    return "\n".join(out) + "\n"
