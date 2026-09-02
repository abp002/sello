"""Comprobación estática: contratos presentes, nombres, tipos y match exhaustivo."""

from __future__ import annotations

from .errors import SelloError
from .nodes import (
    ANY, BOOL, INT, TEXT, Binary, TText, BoolLit, Call, Expr, Fn, If, IntLit, ListLit, Match,
    Name, NoneLit, PCons, PEmpty, PNone, PSome, PWild, Program, SomeExpr, TAny, TextLit,
    TList, TOption, Type, Unary, unify,
)
from .pretty import unparse

Env = dict[str, Type]


def _name(fn: Fn | None) -> str | None:
    return fn.name if fn else None


def signature(fn: Fn) -> str:
    ps = ", ".join(f"{p.name}: {p.type}" for p in fn.params)
    return f"{fn.name}({ps}) -> {fn.ret}"


class Checker:
    def __init__(self, program: Program) -> None:
        self.program = program
        self.fns: dict[str, Fn] = {}

    def check(self) -> None:
        for fn in self.program.fns:
            if _name(fn) in self.fns:
                raise SelloError("E402", f"`{_name(fn)}` is defined twice", fn.line, fn.col, _name(fn))
            self.fns[_name(fn)] = fn
        for fn in self.program.fns:
            self.check_fn(fn)

    # ---- por función ----
    def check_fn(self, fn: Fn) -> None:
        missing = [n for n, v in (("requires", fn.requires), ("ensures", fn.ensures),
                                  ("effects", fn.effects)) if not v]
        if not fn.examples:
            missing.append("example")
        if missing:
            raise SelloError("E100", f"`{_name(fn)}` lacks {', '.join(f'`{m}`' for m in missing)}",
                             fn.line, fn.col, _name(fn))
        if fn.effects != "pure":
            raise SelloError("E101", f"`{fn.effects}` in `{_name(fn)}`", fn.line, fn.col, _name(fn))

        seen: set[str] = set()
        for p in fn.params:
            if p.name in seen:
                raise SelloError("E402", f"parameter `{p.name}` repeated in `{_name(fn)}`",
                                 fn.line, fn.col, _name(fn))
            seen.add(p.name)
        env: Env = {p.name: p.type for p in fn.params}

        for r in fn.requires:
            self.expect(r, env, BOOL, fn, "`requires` must be Bool")
        for en in fn.ensures:
            self.expect(en, {**env, "result": fn.ret}, BOOL, fn, "`ensures` must be Bool")
        for ex in fn.examples:
            self.expect(ex, {}, BOOL, fn, "`example` must be Bool (usually `call == expected`)")
        self.expect(fn.body, env, fn.ret, fn, f"body of `{_name(fn)}` must return {fn.ret}")

    def expect(self, e: Expr, env: Env, want: Type, fn: Fn | None, why: str) -> Type:
        got = self.type_of(e, env, fn)
        u = unify(got, want)
        if u is None:
            raise SelloError("E400", f"{why}: expected {want}, got {got} in `{unparse(e)}`",
                             e.line, e.col, _name(fn), {"expected": str(want), "actual": str(got)})
        return u

    # ---- expresiones ----
    def type_of(self, e: Expr, env: Env, fn: Fn | None) -> Type:
        if isinstance(e, IntLit):
            return INT
        if isinstance(e, BoolLit):
            return BOOL
        if isinstance(e, TextLit):
            return TEXT
        if isinstance(e, NoneLit):
            return TOption(ANY)
        if isinstance(e, SomeExpr):
            return TOption(self.type_of(e.inner, env, fn))
        if isinstance(e, ListLit):
            elem: Type = ANY
            for item in e.items:
                elem = self.expect(item, env, elem, fn, "list elements must share a type")
            return TList(elem)
        if isinstance(e, Name):
            if e.id in env:
                return env[e.id]
            hint = " (`result` is only valid inside `ensures`)" if e.id == "result" else ""
            raise SelloError("E401", f"`{e.id}`{hint}", e.line, e.col, _name(fn))
        if isinstance(e, Call):
            callee = self.fns.get(e.name)
            if callee is None:
                raise SelloError("E401", f"function `{e.name}`", e.line, e.col, _name(fn))
            if len(e.args) != len(callee.params):
                raise SelloError("E403", f"`{e.name}` takes {len(callee.params)}, got {len(e.args)}",
                                 e.line, e.col, _name(fn))
            for arg, p in zip(e.args, callee.params):
                self.expect(arg, env, p.type, fn, f"argument `{p.name}` of `{e.name}`")
            return callee.ret
        if isinstance(e, Unary):
            if e.op == "not":
                self.expect(e.operand, env, BOOL, fn, "`not` needs Bool")
                return BOOL
            self.expect(e.operand, env, INT, fn, "unary `-` needs Int")
            return INT
        if isinstance(e, Binary):
            if e.op == "++":
                lt = self.type_of(e.left, env, fn)
                if not isinstance(lt, (TList, TText, TAny)):
                    raise SelloError("E400", f"`++` needs List or Text, got {lt} in `{unparse(e)}`",
                                     e.line, e.col, _name(fn), {"expected": "List[T] or Text", "actual": str(lt)})
                return self.expect(e.right, env, lt, fn, "both sides of `++` must share a type")
            if e.op in ("+", "-", "*", "/", "%"):
                self.expect(e.left, env, INT, fn, f"`{e.op}` needs Int")
                self.expect(e.right, env, INT, fn, f"`{e.op}` needs Int")
                return INT
            if e.op in ("<", "<=", ">", ">="):
                self.expect(e.left, env, INT, fn, f"`{e.op}` needs Int")
                self.expect(e.right, env, INT, fn, f"`{e.op}` needs Int")
                return BOOL
            if e.op in ("==", "!="):
                lt = self.type_of(e.left, env, fn)
                self.expect(e.right, env, lt, fn, f"both sides of `{e.op}` must share a type")
                return BOOL
            if e.op in ("and", "or"):
                self.expect(e.left, env, BOOL, fn, f"`{e.op}` needs Bool")
                self.expect(e.right, env, BOOL, fn, f"`{e.op}` needs Bool")
                return BOOL
            raise SelloError("E000", f"unknown operator {e.op}", e.line, e.col, _name(fn))
        if isinstance(e, If):
            self.expect(e.cond, env, BOOL, fn, "`if` condition must be Bool")
            t = self.type_of(e.then, env, fn)
            return self.expect(e.otherwise, env, t, fn, "`then` and `else` must share a type")
        if isinstance(e, Match):
            return self.type_of_match(e, env, fn)
        raise TypeError(f"nodo desconocido: {e!r}")

    def type_of_match(self, e: Match, env: Env, fn: Fn | None) -> Type:
        st = self.type_of(e.subject, env, fn)
        result: Type = ANY
        covered: set[str] = set()
        for arm in e.arms:
            p = arm.pattern
            arm_env = dict(env)
            if isinstance(p, PEmpty) or isinstance(p, PCons):
                if not isinstance(st, (TList, TAny)):
                    raise SelloError("E400", f"list pattern on {st} in `{unparse(e.subject)}`",
                                     p.line, p.col, _name(fn))
                elem = st.elem if isinstance(st, TList) else ANY
                if isinstance(p, PCons):
                    if p.head != "_":
                        arm_env[p.head] = elem
                    if p.tail != "_":
                        arm_env[p.tail] = TList(elem)
                    covered.add("cons")
                else:
                    covered.add("empty")
            elif isinstance(p, (PNone, PSome)):
                if not isinstance(st, (TOption, TAny)):
                    raise SelloError("E400", f"option pattern on {st} in `{unparse(e.subject)}`",
                                     p.line, p.col, _name(fn))
                elem = st.elem if isinstance(st, TOption) else ANY
                if isinstance(p, PSome):
                    arm_env[p.name] = elem
                    covered.add("some")
                else:
                    covered.add("none")
            elif isinstance(p, PWild):
                if p.name:
                    arm_env[p.name] = st
                covered.add("wild")
            result = self.expect(arm.body, arm_env, result, fn, "match arms must share a type")

        if "wild" not in covered:
            if isinstance(st, TList) and covered != {"empty", "cons"}:
                raise SelloError("E404", f"match on {st} needs `[]` and `[h, ..t]`", e.line, e.col, _name(fn))
            if isinstance(st, TOption) and covered != {"none", "some"}:
                raise SelloError("E404", f"match on {st} needs `None` and `Some(x)`", e.line, e.col, _name(fn))
            if not isinstance(st, (TList, TOption, TAny)):
                raise SelloError("E404", f"match on {st} needs `_ =>`", e.line, e.col, _name(fn))
        return result
