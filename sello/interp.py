"""Intérprete tree-walking con contratos: requires al llamar, ensures al volver."""

from __future__ import annotations

import sys

from . import builtins
from .errors import SelloError
from .nodes import (
    Binary, BoolLit, Call, Expr, Fn, If, IntLit, ListLit, Match, Name, NoneLit, PCons,
    PEmpty, PNone, PSome, PWild, Program, Quant, SomeExpr, TextLit, Unary,
)
from .pretty import unparse

sys.setrecursionlimit(max(sys.getrecursionlimit(), 20000))


class Some:
    __slots__ = ("value",)

    def __init__(self, value: object) -> None:
        self.value = value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Some) and self.value == other.value

    def __hash__(self) -> int:
        return hash(("Some", self.value))

    def __repr__(self) -> str:
        return f"Some({self.value!r})"


class _NoneV:
    __slots__ = ()

    def __repr__(self) -> str:
        return "None"


NONE = _NoneV()
Value = object


def fmt(v: Value) -> str:
    """Un valor en sintaxis Sello, para errores y salida."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(v, list):
        return "[" + ", ".join(fmt(x) for x in v) + "]"
    if isinstance(v, Some):
        return f"Some({fmt(v.value)})"
    if v is NONE:
        return "None"
    raise TypeError(f"valor desconocido: {v!r}")


Env = dict[str, Value]


class Interpreter:
    def __init__(self, program: Program) -> None:
        self.fns: dict[str, Fn] = {f.name: f for f in program.fns}

    def call(self, name: str, args: list[Value], line: int = 0, col: int = 0,
             caller: str | None = None) -> Value:
        fn = self.fns[name]
        env: Env = {p.name: a for p, a in zip(fn.params, args)}
        shown = f"{name}(" + ", ".join(fmt(a) for a in args) + ")"
        for r in fn.requires:
            if not self.eval(r, env, name):
                raise SelloError("E300", f"{shown} violates `requires {unparse(r)}`",
                                 line, col, caller or name, {"call": shown})
        try:
            value = self.eval(fn.body, env, name)
        except RecursionError:
            raise SelloError("E500", f"recursion too deep in {shown}", fn.line, fn.col, name) from None
        for en in fn.ensures:
            if not self.eval(en, {**env, "result": value}, name):
                raise SelloError("E201", f"{shown} returned {fmt(value)}, which violates "
                                 f"`ensures {unparse(en)}`", fn.line, fn.col, name,
                                 {"call": shown, "got": fmt(value)})
        return value

    def eval(self, e: Expr, env: Env, fn: str | None = None) -> Value:
        if isinstance(e, IntLit):
            return e.value
        if isinstance(e, BoolLit):
            return e.value
        if isinstance(e, TextLit):
            return e.value
        if isinstance(e, NoneLit):
            return NONE
        if isinstance(e, SomeExpr):
            return Some(self.eval(e.inner, env, fn))
        if isinstance(e, ListLit):
            return [self.eval(x, env, fn) for x in e.items]
        if isinstance(e, Name):
            return env[e.id]
        if isinstance(e, Call):
            args = [self.eval(a, env, fn) for a in e.args]
            if e.name in builtins.NAMES:
                return builtins.run(e.name, args)
            return self.call(e.name, args, e.line, e.col, fn)
        if isinstance(e, Unary):
            v = self.eval(e.operand, env, fn)
            return (not v) if e.op == "not" else -v  # type: ignore[operator]
        if isinstance(e, Binary):
            if e.op == "and":
                return bool(self.eval(e.left, env, fn)) and bool(self.eval(e.right, env, fn))
            if e.op == "or":
                return bool(self.eval(e.left, env, fn)) or bool(self.eval(e.right, env, fn))
            l = self.eval(e.left, env, fn)
            r = self.eval(e.right, env, fn)
            if e.op in ("+", "++"): return l + r  # type: ignore[operator]
            if e.op == "-": return l - r  # type: ignore[operator]
            if e.op == "*": return l * r  # type: ignore[operator]
            if e.op in ("/", "%"):
                if r == 0:
                    raise SelloError("E500", f"division by zero in `{unparse(e)}`", e.line, e.col, fn)
                return l // r if e.op == "/" else l % r  # type: ignore[operator]
            if e.op == "==": return l == r
            if e.op == "!=": return l != r
            if e.op == "<": return l < r  # type: ignore[operator]
            if e.op == "<=": return l <= r  # type: ignore[operator]
            if e.op == ">": return l > r  # type: ignore[operator]
            if e.op == ">=": return l >= r  # type: ignore[operator]
            raise SelloError("E000", f"unknown operator {e.op}", e.line, e.col, fn)
        if isinstance(e, If):
            branch = e.then if self.eval(e.cond, env, fn) else e.otherwise
            return self.eval(branch, env, fn)
        if isinstance(e, Match):
            subject = self.eval(e.subject, env, fn)
            for arm in e.arms:
                bound = self.match(arm.pattern, subject)
                if bound is not None:
                    return self.eval(arm.body, {**env, **bound}, fn)
            raise SelloError("E500", f"no arm matches {fmt(subject)} in `{unparse(e)}`", e.line, e.col, fn)
        if isinstance(e, Quant):
            xs = self.eval(e.subject, env, fn)
            holds = (self.eval(e.body, {**env, e.var: x}, fn) for x in xs)  # type: ignore[union-attr]
            return all(holds) if e.kind == "forall" else any(holds)
        raise TypeError(f"nodo desconocido: {e!r}")

    @staticmethod
    def match(p: object, v: Value) -> Env | None:
        if isinstance(p, PEmpty):
            return {} if isinstance(v, list) and not v else None
        if isinstance(p, PCons):
            if not (isinstance(v, list) and v):
                return None
            return {k: x for k, x in ((p.head, v[0]), (p.tail, v[1:])) if k != "_"}
        if isinstance(p, PNone):
            return {} if v is NONE else None
        if isinstance(p, PSome):
            return {p.name: v.value} if isinstance(v, Some) else None
        if isinstance(p, PWild):
            return {p.name: v} if p.name else {}
        raise TypeError(f"patrón desconocido: {p!r}")
