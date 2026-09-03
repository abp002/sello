#!/usr/bin/env python3
"""Mutantes del cuerpo: de los bugs que el juez débil deja pasar, cuántos caza el contrato.

Toma las soluciones aceptadas de corridas del juez (`resultados/juez-*.jsonl`), mete en
cada una un bug pequeño en el cuerpo (nunca en el contrato, los ejemplos ni un `assert`)
y pasa cada mutante por el mismo juez débil y el mismo oráculo que `harness3`. Sin
llamadas al modelo: determinista y gratis. Diseño y prerregistración en el vault:
'Los mutantes del cuerpo miden lo que el ensures caza'.

    uv run python bench/mutantes.py bench/resultados/juez-A.jsonl bench/resultados/juez-B.jsonl
    uv run python bench/mutantes.py bench/resultados/juez-A.jsonl --only nth --cond sello   # humo

Si un (problema, condición, modelo) aparece en varios ficheros, manda el último.
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import RESULTADOS  # noqa: E402
from harness3 import CONDS, PROBLEMAS, ejecutar  # noqa: E402
import juez  # noqa: E402

from sello.nodes import (  # noqa: E402
    Binary, Call, If, IntLit, ListLit, Match, Name, PCons, PSome, PWild, Program, SomeExpr, Unary,
)
from sello.parser import parse  # noqa: E402
from sello.pretty import unparse, unparse_fn  # noqa: E402

TIMEOUT = 60  # el mismo que harness3

# ---------- destinos de un mutante ----------

NO_COMPILA, MUERTO, EQUIVALENTE, SILENCIOSO, CAZADO, RUIDOSO = (
    "no_compila", "muerto", "equivalente", "silencioso", "cazado", "ruidoso")
DESTINOS = (NO_COMPILA, MUERTO, EQUIVALENTE, SILENCIOSO, CAZADO, RUIDOSO)
LLEGAN = (SILENCIOSO, CAZADO, RUIDOSO)

# Errores del checker: el mutante no llega a ejecutarse. E000 no está: un mutante sale de
# un AST válido, así que un E000 sería un fallo del proceso, no del programa.
ESTATICOS = {"E100", "E101", "E102", "E400", "E401", "E402", "E403", "E404"}

# De qué muere un mutante que sí cargó y el juez débil rechazó.
EJEMPLOS, CONTRATO, FRONTERA = "ejemplos", "contrato", "frontera"
OPS = ("frontera", "aritmetica", "literal", "logica", "ramas", "argumentos", "variable")


def clasificar(juez_ok: bool, señal: str | None, dominio: list[str]) -> str:
    """juez_ok/señal: lo que dijo el juez débil. dominio: resultados brutos (ok, wrong,
    caught, reject) de las llamadas del oráculo en el dominio. Ver la nota del vault."""
    if not juez_ok:
        return NO_COMPILA if señal in ESTATICOS else MUERTO
    if juez.WRONG in dominio:
        return SILENCIOSO
    if juez.CAUGHT in dominio:
        return CAZADO
    if juez.REJECT in dominio:
        return RUIDOSO
    return EQUIVALENTE


def causa_muerte(señal: str | None) -> str:
    if señal in ("E200", "wrong"):
        return EJEMPLOS
    if señal in ("E201", "assert"):
        return CONTRATO
    return FRONTERA  # E300, E500, raise, timeout, load, E000


# ---------- huecos del AST ----------

class Slot:
    """Un hueco: atributo de un nodo o posición de una lista. Sirve para los dos AST."""
    __slots__ = ("holder", "key")

    def __init__(self, holder: object, key: object) -> None:
        self.holder, self.key = holder, key

    def get(self) -> object:
        return self.holder[self.key] if isinstance(self.holder, list) else getattr(self.holder, self.key)  # type: ignore[index]

    def set(self, v: object) -> None:
        if isinstance(self.holder, list):
            self.holder[self.key] = v  # type: ignore[index]
        else:
            setattr(self.holder, self.key, v)


Cambios = list[tuple[Slot, object]]
Sitio = tuple[str, Slot, Cambios]  # (operador, hueco del nodo que se describe, cambios)


def _aplicar(cambios: Cambios) -> Cambios:
    olds = [(s, s.get()) for s, _ in cambios]
    for s, v in cambios:
        s.set(v)
    return olds


def _desc(antes: str, despues: str, n: int = 70) -> str:
    corta = lambda s: s if len(s) <= n else s[: n - 1] + "…"  # noqa: E731
    return f"{corta(antes)} -> {corta(despues)}"


def _generar(program: object, texto, fns: list, sitios_de, nombre_de, unparse_nodo) -> tuple[str, list[dict]]:
    """Recorre las funciones, aplica cada sitio, escribe el programa y deshace. Común a
    los dos lenguajes. Devuelve (texto canónico del original, mutantes sin repetidos)."""
    canon = texto(program)
    seen = {canon}
    out: list[dict] = []
    for fn in fns:
        for op, slot, cambios in sitios_de(fn):
            antes = unparse_nodo(slot.get())
            olds = _aplicar(cambios)
            despues = unparse_nodo(slot.get())
            code = texto(program)
            _aplicar(olds)
            if code in seen:
                continue
            seen.add(code)
            out.append({"op": op, "fn": nombre_de(fn), "desc": _desc(antes, despues), "code": code})
    return canon, out


# ---------- Sello ----------

REL = {"<": "<=", "<=": "<", ">": ">=", ">=": ">", "==": "!=", "!=": "=="}
ARIT = {"+": "-", "-": "+", "*": "+", "/": "%", "%": "/"}
LOGIC = {"and": "or", "or": "and"}


def _ligadas(p: object) -> list[str]:
    if isinstance(p, PCons):
        return [n for n in (p.head, p.tail) if n != "_"]
    if isinstance(p, PSome):
        return [p.name]
    if isinstance(p, PWild) and p.name:
        return [p.name]
    return []


def _sitios_sello(e: object, slot: Slot, scope: list[str], out: list[Sitio]) -> None:
    if isinstance(e, Binary):
        for op, tabla in (("frontera", REL), ("aritmetica", ARIT), ("logica", LOGIC)):
            if e.op in tabla:
                out.append((op, slot, [(Slot(e, "op"), tabla[e.op])]))
    elif isinstance(e, IntLit):
        for d in (1, -1):
            out.append(("literal", slot, [(Slot(e, "value"), e.value + d)]))
    elif isinstance(e, Unary):
        out.append(("logica" if e.op == "not" else "aritmetica", slot, [(slot, e.operand)]))
    elif isinstance(e, If):
        out.append(("ramas", slot, [(Slot(e, "then"), e.otherwise), (Slot(e, "otherwise"), e.then)]))
    elif isinstance(e, Call) and len(e.args) >= 2:
        out.append(("argumentos", slot, [(Slot(e.args, 0), e.args[1]), (Slot(e.args, 1), e.args[0])]))
    elif isinstance(e, Name):
        for other in scope:
            if other != e.id:
                out.append(("variable", slot, [(Slot(e, "id"), other)]))

    if isinstance(e, SomeExpr):
        _sitios_sello(e.inner, Slot(e, "inner"), scope, out)
    elif isinstance(e, ListLit):
        for i, x in enumerate(e.items):
            _sitios_sello(x, Slot(e.items, i), scope, out)
    elif isinstance(e, Call):
        for i, a in enumerate(e.args):
            _sitios_sello(a, Slot(e.args, i), scope, out)
    elif isinstance(e, Unary):
        _sitios_sello(e.operand, Slot(e, "operand"), scope, out)
    elif isinstance(e, Binary):
        _sitios_sello(e.left, Slot(e, "left"), scope, out)
        _sitios_sello(e.right, Slot(e, "right"), scope, out)
    elif isinstance(e, If):
        for k in ("cond", "then", "otherwise"):
            _sitios_sello(getattr(e, k), Slot(e, k), scope, out)
    elif isinstance(e, Match):
        _sitios_sello(e.subject, Slot(e, "subject"), scope, out)
        for arm in e.arms:
            _sitios_sello(arm.body, Slot(arm, "body"), scope + _ligadas(arm.pattern), out)


def mutar_sello(src: str) -> tuple[str, list[dict]]:
    program = parse(src)

    def sitios(fn) -> list[Sitio]:
        out: list[Sitio] = []
        _sitios_sello(fn.body, Slot(fn, "body"), [p.name for p in fn.params], out)
        return out

    return _generar(program, lambda p: "\n\n".join(unparse_fn(f) for f in p.fns) + "\n",
                    program.fns, sitios, lambda fn: fn.name, unparse)


# ---------- Python ----------

PYREL = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Eq: ast.NotEq, ast.NotEq: ast.Eq}
PYARIT = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Add, ast.FloorDiv: ast.Mod, ast.Mod: ast.FloorDiv}
PYLOGIC = {ast.And: ast.Or, ast.Or: ast.And}


def _sitios_py(n: ast.AST, slot: Slot, scope: list[str], out: list[Sitio]) -> None:
    # El contrato no se toca; una función anidada se recorre como función propia.
    if isinstance(n, (ast.Assert, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return
    if isinstance(n, ast.Compare):
        for i, op in enumerate(n.ops):
            if type(op) in PYREL:
                out.append(("frontera", slot, [(Slot(n.ops, i), PYREL[type(op)]())]))
    elif isinstance(n, ast.BinOp) and type(n.op) in PYARIT:
        out.append(("aritmetica", slot, [(Slot(n, "op"), PYARIT[type(n.op)]())]))
    elif isinstance(n, ast.BoolOp) and type(n.op) in PYLOGIC:
        out.append(("logica", slot, [(Slot(n, "op"), PYLOGIC[type(n.op)]())]))
    elif isinstance(n, ast.Constant) and type(n.value) is int:
        for d in (1, -1):
            out.append(("literal", slot, [(Slot(n, "value"), n.value + d)]))
    elif isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.Not, ast.USub)):
        out.append(("logica" if isinstance(n.op, ast.Not) else "aritmetica", slot, [(slot, n.operand)]))
    elif isinstance(n, (ast.If, ast.IfExp)) and n.orelse:
        out.append(("ramas", slot, [(Slot(n, "body"), n.orelse), (Slot(n, "orelse"), n.body)]))
    elif isinstance(n, ast.Call) and len(n.args) >= 2:
        out.append(("argumentos", slot, [(Slot(n.args, 0), n.args[1]), (Slot(n.args, 1), n.args[0])]))
    elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
        for other in scope:
            if other != n.id:
                out.append(("variable", slot, [(Slot(n, "id"), other)]))

    for field, value in ast.iter_fields(n):
        if isinstance(value, list):
            for i, x in enumerate(value):
                if isinstance(x, ast.AST):
                    _sitios_py(x, Slot(value, i), scope, out)
        elif isinstance(value, ast.AST):
            _sitios_py(value, Slot(n, field), scope, out)


def mutar_python(src: str) -> tuple[str, list[dict]]:
    tree = ast.parse(src)
    fns = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]

    def sitios(fn: ast.FunctionDef) -> list[Sitio]:
        a = fn.args
        scope = sorted({x.arg for x in a.posonlyargs + a.args + a.kwonlyargs}
                       | {x.id for x in ast.walk(fn) if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Store)})
        out: list[Sitio] = []
        for i, st in enumerate(fn.body):
            _sitios_py(st, Slot(fn.body, i), scope, out)
        return out

    return _generar(tree, lambda t: ast.unparse(t) + "\n", fns, sitios, lambda fn: fn.name, ast.unparse)


def mutar(cond: str, src: str) -> tuple[str, list[dict]]:
    return (mutar_sello if cond == "sello" else mutar_python)(src)


# ---------- ejecución ----------

def _señal(cond: str, r: list[dict] | dict) -> tuple[bool, str | None]:
    """Lo que dijo el juez débil: (aceptado, señal del primer fallo)."""
    if isinstance(r, dict):
        return False, (r["error"].get("code", "E000") if cond == "sello" else "load")
    for c in r:
        if c["result"] != juez.OK:
            d = c.get("detail") or {}
            if cond == "sello":
                return False, (d["error"].get("code", "E000") if "error" in d else "wrong")
            return False, d.get("status", "wrong")
    return True, None


def _cuenta(resultados: list[str]) -> dict:
    return {k: resultados.count(k) for k in (juez.OK, juez.WRONG, juez.CAUGHT, juez.REJECT)}


def evaluar(cond: str, code: str, p: dict) -> dict:
    """Juez débil y, si acepta, oráculo. Devuelve el destino y los recuentos por zona."""
    ok, señal = _señal(cond, ejecutar(cond, code, p, p["visible"], TIMEOUT))
    dom: list[str] = []
    amb: list[str] = []
    if ok:
        o = ejecutar(cond, code, p, p["oracle"], TIMEOUT)
        casos = [{**c, "result": juez.REJECT} for c in p["oracle"]] if isinstance(o, dict) else o
        dom = [c["result"] for c in casos if c["zone"] == "domain"]
        amb = [c["result"] for c in casos if c["zone"] != "domain"]
    cat = clasificar(ok, señal, dom)
    if señal == "E000":
        print(f"  aviso: E000 en un mutante de {p['fn']} ({cond}); el proceso falló, no el programa", file=sys.stderr)
    return {"cat": cat, "juez_ok": ok, "señal": señal,
            "muerte": causa_muerte(señal) if cat == MUERTO else None,
            "dom": _cuenta(dom), "amb": _cuenta(amb)}


# ---------- recuento y tabla ----------

def contar(muts: list[dict]) -> dict:
    c = {k: 0 for k in ("generados", *DESTINOS, "llegan", f"muerto_{EJEMPLOS}", f"muerto_{CONTRATO}",
                        f"muerto_{FRONTERA}", "llamadas_wrong", "llamadas_caught")}
    c["silencioso_por_op"] = {op: 0 for op in OPS}
    c["llegan_por_op"] = {op: 0 for op in OPS}
    for m in muts:
        c["generados"] += 1
        c[m["cat"]] += 1
        if m["cat"] == MUERTO:
            c[f"muerto_{m['muerte']}"] += 1
        if m["cat"] in LLEGAN:
            c["llegan"] += 1
            c["llegan_por_op"][m["op"]] += 1
            c["llamadas_wrong"] += m["dom"][juez.WRONG]
            c["llamadas_caught"] += m["dom"][juez.CAUGHT]
            if m["cat"] == SILENCIOSO:
                c["silencioso_por_op"][m["op"]] += 1
    return c


def _pct(a: int, b: int) -> str:
    return f"{a}/{b} ({100 * a / b:.0f} %)" if b else "-"


def resumen(rows: list[dict], when: str) -> str:
    cols = sorted({(r["cond"], r["model"]) for r in rows}, key=lambda x: (CONDS.index(x[0]), x[1]))
    name = lambda c: f"{c[0]}·{c[1]}"  # noqa: E731
    probs = sorted({r["problem"] for r in rows})
    by = {(r["problem"], r["cond"], r["model"]): r for r in rows}
    head = "| " + " | ".join(name(c) for c in cols) + " |"
    sep = "|---|" + "---|" * len(cols)
    out = [f"# Mutantes del cuerpo {when}", "",
           "Por solución aceptada: mutantes que llegan a producción (pasan el juez débil y no son "
           "equivalentes en el dominio) y, de ellos, cuántos quedan silenciosos y cuántos caza el "
           "contrato. Formato: silenciosos/llegan · cazados. Prerregistrado en el vault: "
           "'Los mutantes del cuerpo miden lo que el ensures caza'.", "",
           "| Problema " + head, sep]
    for pr in probs:
        cells = []
        for c in cols:
            r = by.get((pr, *c))
            if r is None:
                cells.append("-")
            else:
                k = r["recuento"]
                cells.append(f"{k[SILENCIOSO]}/{k['llegan']} · {k[CAZADO]}")
        out.append(f"| {pr} | " + " | ".join(cells) + " |")

    out += ["", "| " + head, sep]

    def rs(c): return [r for r in rows if (r["cond"], r["model"]) == c]
    def suma(c, k): return sum(r["recuento"][k] for r in rs(c))
    def stat(label, f): out.append(f"| {label} | " + " | ".join(f(c) for c in cols) + " |")

    stat("soluciones", lambda c: str(len(rs(c))))
    stat("mutantes generados", lambda c: str(suma(c, "generados")))
    stat("no compilan (checker)", lambda c: _pct(suma(c, NO_COMPILA), suma(c, "generados")))
    stat("muertos por el juez débil", lambda c: _pct(suma(c, MUERTO), suma(c, "generados")))
    stat("· por ejemplos (E200 / caso visible)", lambda c: str(suma(c, f"muerto_{EJEMPLOS}")))
    stat("· por el contrato (E201 / assert)", lambda c: str(suma(c, f"muerto_{CONTRATO}")))
    stat("· en la frontera (E300 / E500 / excepción / timeout)", lambda c: str(suma(c, f"muerto_{FRONTERA}")))
    stat("equivalentes en el dominio", lambda c: str(suma(c, EQUIVALENTE)))
    stat("**llegan a producción**", lambda c: f"**{suma(c, 'llegan')}**")
    stat("**silenciosos / llegan**", lambda c: f"**{_pct(suma(c, SILENCIOSO), suma(c, 'llegan'))}**")
    stat("cazados por el contrato / llegan", lambda c: _pct(suma(c, CAZADO), suma(c, "llegan")))
    stat("ruidosos / llegan", lambda c: _pct(suma(c, RUIDOSO), suma(c, "llegan")))
    stat("por llamada: incorrectos cazados / (cazados + silenciosos)",
         lambda c: _pct(suma(c, "llamadas_caught"), suma(c, "llamadas_caught") + suma(c, "llamadas_wrong")))

    out += ["", "Silenciosos por operador (silenciosos/llegan):", "", "| operador " + head, sep]
    for op in OPS:
        def cell(c, op=op):
            s = sum(r["recuento"]["silencioso_por_op"][op] for r in rs(c))
            ll = sum(r["recuento"]["llegan_por_op"][op] for r in rs(c))
            return f"{s}/{ll}" if ll else "-"
        out.append(f"| {op} | " + " | ".join(cell(c) for c in cols) + " |")
    return "\n".join(out) + "\n"


# ---------- corrida ----------

def cargar(paths: list[Path], conds: list[str], only: str | None) -> list[dict]:
    """Soluciones aceptadas, una por (problema, condición, modelo); manda el último fichero."""
    sel: dict[tuple, dict] = {}
    for path in paths:
        for line in path.read_text().splitlines():
            r = json.loads(line)
            if r["cond"] in conds and r.get("code") and r.get("accepted_at") and (not only or r["problem"] == only):
                sel[(r["problem"], r["cond"], r["model"])] = {"problem": r["problem"], "cond": r["cond"],
                                                             "model": r["model"], "code": r["code"], "origen": path.name}
    return [sel[k] for k in sorted(sel)]


def procesar(sol: dict, p: dict, pool: ThreadPoolExecutor) -> dict:
    cond = sol["cond"]
    canon, muts = mutar(cond, sol["code"])
    base = evaluar(cond, canon, p)
    if not base["juez_ok"]:
        print(f"  aviso: el original de {sol['problem']} ({cond}, {sol['model']}) no pasa el juez débil "
              f"tras reescribirlo: {base['señal']}", file=sys.stderr)
    for m, r in zip(muts, pool.map(lambda m: evaluar(cond, m["code"], p), muts)):
        m.update(r)
    k = contar(muts)
    print(f"  {sol['problem']:<15} {cond:<15} {sol['model']:<7} {k['generados']:>3} mutantes · "
          f"no compilan {k[NO_COMPILA]} · muertos {k[MUERTO]} · equivalentes {k[EQUIVALENTE]} · "
          f"llegan {k['llegan']}: silenciosos {k[SILENCIOSO]}, cazados {k[CAZADO]}, ruidosos {k[RUIDOSO]}",
          file=sys.stderr, flush=True)
    return {**sol, "code": canon, "original": base, "mutantes": muts, "recuento": k}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("jsonl", nargs="+", type=Path, help="corridas del juez de las que tomar las soluciones")
    ap.add_argument("--cond", nargs="+", choices=CONDS, default=CONDS)
    ap.add_argument("--only", help="nombre de un problema")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    probs = {p["fn"]: p for p in (json.loads(f.read_text()) for f in sorted(PROBLEMAS.glob("*.json")))}
    sols = cargar(args.jsonl, args.cond, args.only)
    when = dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    print(f"{len(sols)} soluciones, {args.workers} workers", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = [procesar(s, probs[s["problem"]], pool) for s in sols]

    RESULTADOS.mkdir(exist_ok=True)
    base = RESULTADOS / (("humo-" if args.only else "") + f"mutantes-{when}")
    with open(base.with_suffix(".jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    md = resumen(rows, when)
    base.with_suffix(".md").write_text(md)
    print(md)
    print(f"detalle: {base.with_suffix('.jsonl')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
