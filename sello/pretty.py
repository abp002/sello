"""Vuelve a escribir un AST como texto Sello. Se usa en mensajes de error."""

from __future__ import annotations

from .nodes import (
    Binary, BoolLit, Call, Expr, If, IntLit, ListLit, Match, Name, NoneLit,
    PCons, PEmpty, PNone, PSome, PWild, Pattern, SomeExpr, TextLit, Unary,
)


def unparse(e: Expr) -> str:
    if isinstance(e, IntLit):
        return str(e.value)
    if isinstance(e, BoolLit):
        return "true" if e.value else "false"
    if isinstance(e, TextLit):
        return '"' + e.value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(e, NoneLit):
        return "None"
    if isinstance(e, SomeExpr):
        return f"Some({unparse(e.inner)})"
    if isinstance(e, ListLit):
        return "[" + ", ".join(unparse(x) for x in e.items) + "]"
    if isinstance(e, Name):
        return e.id
    if isinstance(e, Call):
        return f"{e.name}(" + ", ".join(unparse(a) for a in e.args) + ")"
    if isinstance(e, Unary):
        return f"not {unparse(e.operand)}" if e.op == "not" else f"-{unparse(e.operand)}"
    if isinstance(e, Binary):
        return f"({unparse(e.left)} {e.op} {unparse(e.right)})"
    if isinstance(e, If):
        return f"if {unparse(e.cond)} then {unparse(e.then)} else {unparse(e.otherwise)}"
    if isinstance(e, Match):
        arms = " ".join(f"{unparse_pat(a.pattern)} => {unparse(a.body)}" for a in e.arms)
        return f"match {unparse(e.subject)} {{ {arms} }}"
    raise TypeError(f"nodo desconocido: {e!r}")


def unparse_pat(p: Pattern) -> str:
    if isinstance(p, PEmpty):
        return "[]"
    if isinstance(p, PCons):
        return f"[{p.head}, ..{p.tail}]"
    if isinstance(p, PNone):
        return "None"
    if isinstance(p, PSome):
        return f"Some({p.name})"
    if isinstance(p, PWild):
        return p.name or "_"
    raise TypeError(f"patrón desconocido: {p!r}")


def unparse_fn(fn) -> str:
    """Formateador canónico: una función completa en texto Sello."""
    ps = ", ".join(f"{p.name}: {p.type}" for p in fn.params)
    lines = [f"fn {fn.name}({ps}) -> {fn.ret}"]
    lines += [f"  requires {unparse(r)}" for r in fn.requires]
    lines += [f"  ensures {unparse(e)}" for e in fn.ensures]
    lines.append(f"  effects {fn.effects}")
    lines += [f"  example {unparse(x)}" for x in fn.examples]
    lines += ["{", f"  {unparse(fn.body)}", "}"]
    return "\n".join(lines)
