"""Direccionamiento por contenido: cada función se identifica por el hash de su forma
canónica. Nombres de parámetros y de función borrados; las llamadas se refieren a otras
funciones por su hash; la recursión mutua se hashea como ciclo (idea de Unison).
"""

from __future__ import annotations

import hashlib

from .builtins import NAMES as BUILTINS
from .nodes import (
    Arm, Binary, BoolLit, Call, Expr, Fn, If, IntLit, ListLit, Match, Name, NoneLit,
    PCons, PEmpty, PNone, PSome, PWild, Program, Quant, SomeExpr, TextLit, Unary, children,
)

Resolve = "callable[[str], str]"


def _h(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def short(h: str) -> str:
    return h[:12]


# ---------- forma canónica ----------

def canon_expr(e: Expr, env: list[str], resolve) -> str:
    """S-expresión con variables por posición de ligadura y llamadas por referencia."""
    if isinstance(e, IntLit):
        return str(e.value)
    if isinstance(e, BoolLit):
        return "#t" if e.value else "#f"
    if isinstance(e, TextLit):
        return '"' + e.value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(e, NoneLit):
        return "None"
    if isinstance(e, SomeExpr):
        return f"(Some {canon_expr(e.inner, env, resolve)})"
    if isinstance(e, ListLit):
        return "(list " + " ".join(canon_expr(x, env, resolve) for x in e.items) + ")"
    if isinstance(e, Name):
        if e.id == "result" and "result" not in env:
            return "$result"
        # índice de De Bruijn: distancia a la ligadura más reciente (la última en env,
        # no la primera: un patrón puede sombrear un parámetro)
        if e.id not in env:
            return f"?{e.id}"
        return f"${len(env) - 1 - max(i for i, v in enumerate(env) if v == e.id)}"
    if isinstance(e, Call):
        ref = f"@{e.name}" if e.name in BUILTINS else resolve(e.name)
        return f"(call {ref} " + " ".join(canon_expr(a, env, resolve) for a in e.args) + ")"
    if isinstance(e, Unary):
        return f"({e.op} {canon_expr(e.operand, env, resolve)})"
    if isinstance(e, Binary):
        return f"({e.op} {canon_expr(e.left, env, resolve)} {canon_expr(e.right, env, resolve)})"
    if isinstance(e, If):
        return (f"(if {canon_expr(e.cond, env, resolve)} {canon_expr(e.then, env, resolve)} "
                f"{canon_expr(e.otherwise, env, resolve)})")
    if isinstance(e, Match):
        arms = " ".join(_canon_arm(a, env, resolve) for a in e.arms)
        return f"(match {canon_expr(e.subject, env, resolve)} {arms})"
    if isinstance(e, Quant):
        return (f"({e.kind} {canon_expr(e.subject, env, resolve)} "
                f"{canon_expr(e.body, env + [e.var], resolve)})")
    raise TypeError(f"nodo desconocido: {e!r}")


def _canon_arm(a: Arm, env: list[str], resolve) -> str:
    p = a.pattern
    if isinstance(p, PEmpty):
        return f"([] {canon_expr(a.body, env, resolve)})"
    if isinstance(p, PCons):
        return f"(:: {canon_expr(a.body, env + [p.head, p.tail], resolve)})"  # `_` ocupa hueco: no importa, nunca se referencia
    if isinstance(p, PNone):
        return f"(None {canon_expr(a.body, env, resolve)})"
    if isinstance(p, PSome):
        return f"(Some {canon_expr(a.body, env + [p.name], resolve)})"
    if isinstance(p, PWild):
        return (f"(bind {canon_expr(a.body, env + [p.name], resolve)})" if p.name
                else f"(_ {canon_expr(a.body, env, resolve)})")
    raise TypeError(f"patrón desconocido: {p!r}")


def canon_fn(fn: Fn, resolve) -> str:
    params = [p.name for p in fn.params]
    parts = ["(fn (" + " ".join(str(p.type) for p in fn.params) + f") {fn.ret}",
             "(requires " + " ".join(canon_expr(r, params, resolve) for r in fn.requires) + ")",
             "(ensures " + " ".join(canon_expr(e, params + ["result"], resolve) for e in fn.ensures) + ")",
             f"(effects {fn.effects})",
             "(examples " + " ".join(canon_expr(x, [], resolve) for x in fn.examples) + ")",
             canon_expr(fn.body, params, resolve) + ")"]
    return " ".join(parts)


# ---------- grafo de llamadas y ciclos ----------

def callees(fn: Fn) -> set[str]:
    out: set[str] = set()

    def walk(e: Expr) -> None:
        if isinstance(e, Call) and e.name not in BUILTINS:
            out.add(e.name)
        for c in children(e):
            walk(c)

    for e in [*fn.requires, *fn.ensures, *fn.examples, fn.body]:
        walk(e)
    return out


def _sccs(graph: dict[str, set[str]]) -> list[list[str]]:
    """Tarjan. Devuelve las componentes en orden topológico inverso (dependencias primero)."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on: set[str] = set()
    out: list[list[str]] = []
    counter = [0]

    def visit(v: str) -> None:
        index[v] = low[v] = counter[0]; counter[0] += 1
        stack.append(v); on.add(v)
        for w in sorted(graph.get(v, ())):
            if w not in graph:
                continue
            if w not in index:
                visit(w); low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop(); on.discard(w); comp.append(w)
                if w == v:
                    break
            out.append(sorted(comp))

    for v in sorted(graph):
        if v not in index:
            visit(v)
    return out


def hash_program(program: Program, external: dict[str, str] | None = None) -> dict[str, str]:
    """Hash de cada función del programa. `external` da hashes de funciones que no están
    en el programa (las del almacén). Devuelve {nombre: hash completo}."""
    fns = {f.name: f for f in program.fns}
    graph = {n: callees(f) for n, f in fns.items()}
    hashes: dict[str, str] = dict(external or {})

    for comp in _sccs(graph):
        if len(comp) == 1:
            n = comp[0]
            def resolve(name: str, n=n) -> str:
                return "$self" if name == n else hashes[name]
            hashes[n] = _h(canon_fn(fns[n], resolve))
            continue
        # ciclo: forma de cada miembro con las referencias internas abstraídas
        def resolve_abs(name: str) -> str:
            return "$cyc" if name in comp else hashes[name]
        forms = sorted((canon_fn(fns[n], resolve_abs), n) for n in comp)
        order = {n: i for i, (_, n) in enumerate(forms)}
        def resolve_idx(name: str) -> str:
            return f"$cyc{order[name]}" if name in comp else hashes[name]
        cycle = _h(" ".join(canon_fn(fns[n], resolve_idx) for _, n in forms))
        for n in comp:
            hashes[n] = _h(f"{cycle}:{order[n]}")
    return hashes
