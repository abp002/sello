"""Parser: tokens -> AST. Recursive descent, sin herramientas."""

from __future__ import annotations

from .errors import SelloError
from .lexer import Token, lex
from .nodes import (
    ANY, BOOL, INT, TEXT, Arm, Binary, BoolLit, Call, Expr, Fn, If, IntLit, ListLit,
    Match, Name, NoneLit, Param, Pattern, PCons, PEmpty, PNone, PSome, PWild, Program,
    Quant, SomeExpr, TextLit, TList, TOption, Type, Unary,
)


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.toks = tokens
        self.i = 0

    # ---- utilidades ----
    @property
    def cur(self) -> Token:
        return self.toks[self.i]

    def at(self, kind: str, value: str | None = None) -> bool:
        t = self.cur
        return t.kind == kind and (value is None or t.value == value)

    def at_sym(self, value: str) -> bool:
        return self.at("SYM", value)

    def at_kw(self, value: str) -> bool:
        return self.at("KW", value)

    def advance(self) -> Token:
        t = self.cur
        if t.kind != "EOF":
            self.i += 1
        return t

    def fail(self, msg: str, tok: Token | None = None) -> SelloError:
        t = tok or self.cur
        got = "end of file" if t.kind == "EOF" else repr(t.value)
        return SelloError("E000", f"{msg}, got {got}", t.line, t.col)

    def expect_sym(self, value: str) -> Token:
        if not self.at_sym(value):
            raise self.fail(f"expected {value!r}")
        return self.advance()

    def expect_kw(self, value: str) -> Token:
        if not self.at_kw(value):
            raise self.fail(f"expected {value!r}")
        return self.advance()

    def expect_name(self) -> Token:
        if not self.at("NAME"):
            raise self.fail("expected a name")
        return self.advance()

    # ---- programa ----
    def program(self) -> Program:
        fns: list[Fn] = []
        while not self.at("EOF"):
            fns.append(self.fn())
        return Program(fns)

    def fn(self) -> Fn:
        start = self.expect_kw("fn")
        name = self.expect_name().value
        self.expect_sym("(")
        params: list[Param] = []
        if not self.at_sym(")"):
            while True:
                pname = self.expect_name().value
                self.expect_sym(":")
                params.append(Param(pname, self.type()))
                if self.at_sym(","):
                    self.advance(); continue
                break
        self.expect_sym(")")
        self.expect_sym("->")
        ret = self.type()

        requires: list[Expr] = []
        ensures: list[Expr] = []
        effects: str | None = None
        examples: list[Expr] = []
        while self.at("KW") and self.cur.value in ("requires", "ensures", "effects", "example"):
            kw = self.advance()
            if kw.value == "requires":
                requires.append(self.expr())
            elif kw.value == "ensures":
                ensures.append(self.expr())
            elif kw.value == "effects":
                if effects is not None:
                    raise self.fail("duplicate `effects`", kw)
                effects = self.expect_name().value
            else:
                examples.append(self.expr())

        self.expect_sym("{")
        body = self.expr()
        self.expect_sym("}")
        return Fn(name, params, ret, requires, ensures, effects, examples, body,
                  line=start.line, col=start.col)

    def type(self) -> Type:
        t = self.expect_name()
        if t.value == "Int":
            return INT
        if t.value == "Bool":
            return BOOL
        if t.value == "Text":
            return TEXT
        if t.value in ("List", "Option"):
            self.expect_sym("[")
            inner = self.type()
            self.expect_sym("]")
            return TList(inner) if t.value == "List" else TOption(inner)
        raise self.fail("expected a type (Int, Bool, Text, List[T], Option[T])", t)

    # ---- expresiones ----
    def expr(self) -> Expr:
        if self.at_kw("if"):
            t = self.advance()
            cond = self.expr()
            self.expect_kw("then")
            then = self.expr()
            self.expect_kw("else")
            otherwise = self.expr()
            return If(cond, then, otherwise, line=t.line, col=t.col)
        if self.at_kw("match"):
            t = self.advance()
            subject = self.expr()
            self.expect_sym("{")
            arms: list[Arm] = []
            while not self.at_sym("}"):
                pat = self.pattern()
                self.expect_sym("=>")
                arms.append(Arm(pat, self.expr()))
            self.expect_sym("}")
            if not arms:
                raise self.fail("match needs at least one arm", t)
            return Match(subject, arms, line=t.line, col=t.col)
        if self.at_kw("forall") or self.at_kw("exists"):
            t = self.advance()
            var = self.expect_name().value
            self.expect_kw("in")
            subject = self.or_()
            self.expect_sym(":")
            body = self.expr()
            return Quant(t.value, var, subject, body, line=t.line, col=t.col)
        return self.or_()

    def or_(self) -> Expr:
        left = self.and_()
        while self.at_kw("or"):
            t = self.advance()
            left = Binary("or", left, self.and_(), line=t.line, col=t.col)
        return left

    def and_(self) -> Expr:
        left = self.not_()
        while self.at_kw("and"):
            t = self.advance()
            left = Binary("and", left, self.not_(), line=t.line, col=t.col)
        return left

    def not_(self) -> Expr:
        if self.at_kw("not"):
            t = self.advance()
            return Unary("not", self.not_(), line=t.line, col=t.col)
        return self.cmp()

    def cmp(self) -> Expr:
        left = self.add()
        if self.at("SYM") and self.cur.value in ("==", "!=", "<", "<=", ">", ">="):
            t = self.advance()
            return Binary(t.value, left, self.add(), line=t.line, col=t.col)
        return left

    def add(self) -> Expr:
        left = self.mul()
        while self.at("SYM") and self.cur.value in ("+", "-", "++"):
            t = self.advance()
            left = Binary(t.value, left, self.mul(), line=t.line, col=t.col)
        return left

    def mul(self) -> Expr:
        left = self.unary()
        while self.at("SYM") and self.cur.value in ("*", "/", "%"):
            t = self.advance()
            left = Binary(t.value, left, self.unary(), line=t.line, col=t.col)
        return left

    def unary(self) -> Expr:
        if self.at_sym("-"):
            t = self.advance()
            return Unary("-", self.unary(), line=t.line, col=t.col)
        return self.primary()

    def primary(self) -> Expr:
        t = self.cur
        if t.kind == "INT":
            self.advance()
            return IntLit(int(t.value), line=t.line, col=t.col)
        if t.kind == "TEXT":
            self.advance()
            return TextLit(t.value, line=t.line, col=t.col)
        if t.kind == "KW":
            if t.value in ("true", "false"):
                self.advance()
                return BoolLit(t.value == "true", line=t.line, col=t.col)
            if t.value == "None":
                self.advance()
                return NoneLit(line=t.line, col=t.col)
            if t.value == "Some":
                self.advance()
                self.expect_sym("(")
                inner = self.expr()
                self.expect_sym(")")
                return SomeExpr(inner, line=t.line, col=t.col)
        if t.kind == "SYM" and t.value == "[":
            self.advance()
            items: list[Expr] = []
            if not self.at_sym("]"):
                while True:
                    items.append(self.expr())
                    if self.at_sym(","):
                        self.advance(); continue
                    break
            self.expect_sym("]")
            return ListLit(items, line=t.line, col=t.col)
        if t.kind == "SYM" and t.value == "(":
            self.advance()
            e = self.expr()
            self.expect_sym(")")
            return e
        if t.kind == "NAME":
            self.advance()
            if self.at_sym("("):
                self.advance()
                args: list[Expr] = []
                if not self.at_sym(")"):
                    while True:
                        args.append(self.expr())
                        if self.at_sym(","):
                            self.advance(); continue
                        break
                self.expect_sym(")")
                return Call(t.value, args, line=t.line, col=t.col)
            return Name(t.value, line=t.line, col=t.col)
        raise self.fail("expected an expression")

    # ---- patrones ----
    def name_or_wild(self) -> str:
        if self.at_sym("_"):
            self.advance()
            return "_"
        return self.expect_name().value

    def pattern(self) -> Pattern:
        t = self.cur
        if self.at_sym("["):
            self.advance()
            if self.at_sym("]"):
                self.advance()
                return PEmpty(line=t.line, col=t.col)
            head = self.name_or_wild()
            self.expect_sym(",")
            self.expect_sym("..")
            tail = self.name_or_wild()
            self.expect_sym("]")
            return PCons(head, tail, line=t.line, col=t.col)
        if self.at_kw("None"):
            self.advance()
            return PNone(line=t.line, col=t.col)
        if self.at_kw("Some"):
            self.advance()
            self.expect_sym("(")
            name = self.expect_name().value
            self.expect_sym(")")
            return PSome(name, line=t.line, col=t.col)
        if self.at_sym("_"):
            self.advance()
            return PWild(None, line=t.line, col=t.col)
        if self.at("NAME"):
            self.advance()
            return PWild(t.value, line=t.line, col=t.col)
        raise self.fail("expected a pattern ([], [h, ..t], [_, ..t], None, Some(x), _ or a name)")


def parse(src: str) -> Program:
    return Parser(lex(src)).program()


def parse_expr(src: str) -> Expr:
    p = Parser(lex(src))
    e = p.expr()
    if not p.at("EOF"):
        raise p.fail("expected end of expression")
    return e
