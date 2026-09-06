#!/usr/bin/env python3
"""Dafny -> Sello: cada spec del benchmark de vericoding como contrato congelado de Sello. Fase 4.

De una spec (`cache/specs/<ID>_specs.dfy`) se toman el preámbulo (`function`, `predicate`) y
el método de `<vc-spec>` (firma, `requires`, `ensures`). Sale un contrato en la forma de la
condición `sello_contrato`: la función principal sin cuerpo y sin ejemplos (el benchmark no
trae casos: los pone el modelo, `contrato.Contrato(ejemplos_libres=True)`), más los helpers
congelados que sus cláusulas necesitan.

Cómo se traduce:

- Los helpers no recursivos se inlinean en los contratos (beta-reducción sin captura, `var`
  incluido): el contrato queda autocontenido y el probador ve las fórmulas, no axiomas.
- Los recursivos quedan como `fn`, con su `requires` de Dafny (o una tautología: Sello exige
  la cláusula), `ensures result == <cuerpo>` (la definición es lo único que un llamador ve por
  contrato) más los `ensures` de Dafny, y `example`s calculados con el intérprete de Sello
  sobre entradas pequeñas.
- `==>` -> `not a or b` · `<==>` -> `==` · `|s|` -> `len(s)` · `x in s` -> `contains(s, x)` ·
  `forall x :: x in s ==> P` -> `forall x in s: P` · `exists x :: x in s && P` -> `exists x in s: P`
  · `+` de secuencias -> `++` · `a <= b < c` -> `a <= b and b < c` · `nat` -> `Int` y `>= 0` en
  `requires`/`ensures` · un `&&` de primer nivel se parte en cláusulas.
- Lo que Sello no tiene (índices `s[i]`, tramos, cuantificadores sobre enteros, `array`, `real`,
  `string`, `set`, `map`, datatypes, varios valores de retorno...) no se traduce: la tarea no
  cabe y se cuenta por qué. `/` y `%` se traducen tal cual: Dafny es euclídeo y Sello redondea
  hacia abajo, coinciden con divisor positivo; si el divisor no es un literal positivo la
  tarea lleva la nota `div`.

    uv run python bench/vericoding/traducir.py              # cobertura sobre la caché; escribe tareas/
    uv run python bench/vericoding/traducir.py DA0001 --ver # una spec, con el contrato y los motivos
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import itertools
import json
import re
import signal
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BENCH = AQUI.parent
ROOT = BENCH.parent
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(ROOT))
import contrato as ct  # noqa: E402
from bajar import CSV, SPECS  # noqa: E402

from sello.builtins import NAMES as BUILTINS  # noqa: E402
from sello.checker import Checker  # noqa: E402
from sello.errors import SelloError  # noqa: E402
from sello.hash import _sccs  # noqa: E402
from sello.interp import Interpreter, fmt  # noqa: E402
from sello.lexer import KEYWORDS  # noqa: E402
from sello.nodes import (  # noqa: E402
    BOOL, INT, Binary, BoolLit, Call, Expr, Fn, If, IntLit, ListLit, Name, Param, Program, Quant,
    TBool, TInt, TList, Type, Unary,
)
from sello.parser import parse, parse_expr  # noqa: E402
from sello.pretty import unparse_fn  # noqa: E402

TAREAS = AQUI / "tareas"
RESULTADOS = BENCH / "resultados"
RESERVADOS = set(KEYWORDS) | set(BUILTINS) | {"result"}
FUENTES = ("apps", "dafnybench", "humaneval", "verina", "verified_cogen", "numpy_triple", "numpy_simple", "bignum")


# ---------- léxico de Dafny ----------

class SintaxisDafny(Exception):
    pass


@dataclass(frozen=True)
class Tok:
    kind: str   # NAME INT REAL STR CHAR SYM EOF
    value: str
    line: int


SYMS = ("<==>", "==>", "<==", "!in", "&&", "||", "==", "!=", "<=", ">=", "::", ":=", ":|", "..", "=>", "->", "~>")
SYM1 = set("()[]{}<>+-*/%!|,:;.=@#&^")


def lex(src: str) -> list[Tok]:
    out: list[Tok] = []
    i, n, line = 0, len(src), 1
    while i < n:
        c = src[i]
        if c == "\n":
            line += 1; i += 1; continue
        if c.isspace():
            i += 1; continue
        if src.startswith("//", i):
            j = src.find("\n", i); i = n if j < 0 else j; continue
        if src.startswith("/*", i):
            depth, j = 1, i + 2
            while j < n and depth:
                if src.startswith("/*", j): depth += 1; j += 2
                elif src.startswith("*/", j): depth -= 1; j += 2
                else:
                    line += src[j] == "\n"; j += 1
            i = j; continue
        if src.startswith("{:", i):  # atributos: fuera
            depth, j = 0, i
            while j < n:
                if src[j] == "{": depth += 1
                elif src[j] == "}":
                    depth -= 1
                    if depth == 0:
                        j += 1; break
                elif src[j] == "\n": line += 1
                j += 1
            i = j; continue
        if c.isdigit():
            j = i
            if src.startswith(("0x", "0X"), i):
                j = i + 2
                while j < n and (src[j] in "0123456789abcdefABCDEF_"): j += 1
                out.append(Tok("INT", str(int(src[i:j].replace("_", ""), 16)), line))
            else:
                while j < n and (src[j].isdigit() or src[j] == "_"): j += 1
                if j + 1 < n and src[j] == "." and src[j + 1].isdigit():
                    j += 1
                    while j < n and (src[j].isdigit() or src[j] == "_"): j += 1
                    out.append(Tok("REAL", src[i:j], line))
                else:
                    out.append(Tok("INT", src[i:j].replace("_", ""), line))
            i = j; continue
        if c.isalpha() or c in "_?":
            j = i
            while j < n and (src[j].isalnum() or src[j] in "_'?"): j += 1
            out.append(Tok("NAME", src[i:j], line)); i = j; continue
        if c == '"' or (c == "@" and i + 1 < n and src[i + 1] == '"'):
            j = i + (2 if c == "@" else 1)
            while j < n and src[j] != '"':
                if src[j] == "\\": j += 1
                j += 1
            out.append(Tok("STR", src[i:j + 1], line)); i = j + 1; continue
        if c == "'":
            j = i + 1
            if j < n and src[j] == "\\": j += 2
            k = src.find("'", j)
            if k < 0:
                raise SintaxisDafny(f"carácter sin cerrar (línea {line})")
            out.append(Tok("CHAR", src[i:k + 1], line)); i = k + 1; continue
        for s in SYMS:
            if src.startswith(s, i):
                if s == "!in" and i + 3 < n and (src[i + 3].isalnum() or src[i + 3] in "_'?"):
                    continue
                out.append(Tok("SYM", s, line)); i += len(s); break
        else:
            if c not in SYM1:
                raise SintaxisDafny(f"carácter inesperado {c!r} (línea {line})")
            out.append(Tok("SYM", c, line)); i += 1
    out.append(Tok("EOF", "", line))
    return out


# ---------- AST de Dafny (el subconjunto que se mira) ----------

@dataclass
class DInt: v: int
@dataclass
class DBool: v: bool
@dataclass
class DName: n: str
@dataclass
class DList: items: list
@dataclass
class DCall: f: str; args: list
@dataclass
class DUn: op: str; e: object
@dataclass
class DBin: op: str; l: object; r: object
@dataclass
class DIf: c: object; a: object; b: object
@dataclass
class DQuant: kind: str; binders: list; rng: object; body: object   # binders: [(nombre, tipo|None, dominio|None)]
@dataclass
class DLet: n: str; init: object; body: object
@dataclass
class DCard: e: object
@dataclass
class DIndex: e: object; i: object
@dataclass
class DSlice: e: object; lo: object; hi: object
@dataclass
class DAs: e: object; t: tuple
@dataclass
class DUnsup: what: str


@dataclass
class Par:
    name: str
    type: tuple


@dataclass
class Func:
    name: str
    params: list[Par]
    ret: tuple
    requires: list
    ensures: list
    body: object | None
    kind: str           # function | predicate
    generic: bool
    retname: str | None
    line: int


@dataclass
class Method:
    name: str
    params: list[Par]
    returns: list[Par]
    requires: list
    ensures: list
    modifies: bool
    generic: bool
    line: int


@dataclass
class Other:
    kind: str
    name: str


def hijos(e) -> list:
    if isinstance(e, DList): return list(e.items)
    if isinstance(e, DCall): return list(e.args)
    if isinstance(e, DUn): return [e.e]
    if isinstance(e, DBin): return [e.l, e.r]
    if isinstance(e, DIf): return [e.c, e.a, e.b]
    if isinstance(e, DQuant):
        return [d for _, _, d in e.binders if d is not None] + ([e.rng] if e.rng is not None else []) + [e.body]
    if isinstance(e, DLet): return [e.init, e.body]
    if isinstance(e, DCard): return [e.e]
    if isinstance(e, DIndex): return [e.e, e.i]
    if isinstance(e, DSlice): return [e.e] + [x for x in (e.lo, e.hi) if x is not None]
    if isinstance(e, DAs): return [e.e]
    return []


def mapa(e, f):
    """El nodo con los hijos pasados por `f`."""
    if isinstance(e, DList): return DList([f(x) for x in e.items])
    if isinstance(e, DCall): return DCall(e.f, [f(a) for a in e.args])
    if isinstance(e, DUn): return DUn(e.op, f(e.e))
    if isinstance(e, DBin): return DBin(e.op, f(e.l), f(e.r))
    if isinstance(e, DIf): return DIf(f(e.c), f(e.a), f(e.b))
    if isinstance(e, DQuant):
        return DQuant(e.kind, [(n, t, None if d is None else f(d)) for n, t, d in e.binders],
                      None if e.rng is None else f(e.rng), f(e.body))
    if isinstance(e, DLet): return DLet(e.n, f(e.init), f(e.body))
    if isinstance(e, DCard): return DCard(f(e.e))
    if isinstance(e, DIndex): return DIndex(f(e.e), f(e.i))
    if isinstance(e, DSlice): return DSlice(f(e.e), None if e.lo is None else f(e.lo), None if e.hi is None else f(e.hi))
    if isinstance(e, DAs): return DAs(f(e.e), e.t)
    return e


def libres(e) -> set[str]:
    if isinstance(e, DName):
        return {e.n}
    if isinstance(e, DQuant):
        out: set[str] = set()
        ligadas: set[str] = set()
        for n, _, d in e.binders:
            if d is not None:
                out |= libres(d) - ligadas
            ligadas.add(n)
        dentro = (libres(e.rng) if e.rng is not None else set()) | libres(e.body)
        return out | (dentro - ligadas)
    if isinstance(e, DLet):
        return libres(e.init) | (libres(e.body) - {e.n})
    out = set()
    for c in hijos(e):
        out |= libres(c)
    return out


def llamadas(e) -> set[str]:
    out = {e.f} if isinstance(e, DCall) else set()
    for c in hijos(e):
        out |= llamadas(c)
    return out


def conjuntos(e) -> list:
    """Los conjuntos de un `&&` (de primer nivel), en orden."""
    if isinstance(e, DBin) and e.op == "&&":
        return conjuntos(e.l) + conjuntos(e.r)
    return [e]


def conjuncion(xs: list):
    out = None
    for x in xs:
        out = x if out is None else DBin("&&", out, x)
    return out


def tipo_texto(t: tuple) -> str:
    if t[0] in ("seq", "set", "iset", "multiset", "array", "array2", "array3"):
        return f"{t[0]}<{tipo_texto(t[1])}>" if len(t) > 1 else t[0]
    if t[0] in ("map", "imap"):
        return f"{t[0]}<{tipo_texto(t[1])}, {tipo_texto(t[2])}>"
    if t[0] == "tuple":
        return "(" + ", ".join(tipo_texto(x) for x in t[1:]) + ")"
    if t[0] == "name":
        return t[1]
    return t[0]


# ---------- parser ----------

TOP = {"function", "predicate", "method", "lemma", "ghost", "static", "opaque", "twostate", "least", "greatest",
       "abstract", "datatype", "codatatype", "class", "trait", "type", "newtype", "const", "module", "iterator",
       "import", "include", "export"}
MODS = {"ghost", "static", "opaque", "twostate", "abstract", "least", "greatest"}
SPECKW = {"requires", "ensures", "decreases", "reads", "modifies"}
CMP = {"==", "!=", "<", "<=", ">", ">=", "in", "!in"}


class Parser:
    def __init__(self, toks: list[Tok]) -> None:
        self.t = toks
        self.i = 0
        self.en_args = 0  # dentro de una lista de argumentos: ahí `i requires P => e` es una lambda

    @property
    def cur(self) -> Tok:
        return self.t[self.i]

    def peek(self, k: int = 1) -> Tok:
        return self.t[min(self.i + k, len(self.t) - 1)]

    def at(self, v: str) -> bool:
        return self.cur.kind in ("SYM", "NAME") and self.cur.value == v

    def adv(self) -> Tok:
        t = self.cur
        if t.kind != "EOF":
            self.i += 1
        return t

    def eat(self, v: str) -> Tok:
        if not self.at(v):
            raise SintaxisDafny(f"esperaba {v!r}, hay {self.cur.value or 'fin'!r} (línea {self.cur.line})")
        return self.adv()

    def name(self) -> str:
        if self.cur.kind != "NAME":
            raise SintaxisDafny(f"esperaba un nombre, hay {self.cur.value or 'fin'!r} (línea {self.cur.line})")
        return self.adv().value

    # ---- declaraciones ----
    def decls(self) -> list:
        out: list = []
        while self.cur.kind != "EOF":
            start = self.i
            try:
                out.append(self.decl())
            except SintaxisDafny as e:
                self.i = start
                kw = self.adv().value
                self.saltar()
                out.append(Other("sintaxis", f"{kw}: {e}"))
        return out

    def saltar(self) -> None:
        """Hasta la siguiente declaración de primer nivel (a profundidad 0 de llaves)."""
        depth = 0
        while self.cur.kind != "EOF":
            if depth == 0 and self.cur.kind == "NAME" and self.cur.value in TOP:
                return
            if self.at("{"):
                depth += 1
            elif self.at("}"):
                depth = max(0, depth - 1)
            self.adv()

    def saltar_par(self, abre: str, cierra: str) -> None:
        depth = 0
        while self.cur.kind != "EOF":
            if self.at(abre):
                depth += 1
            elif self.at(cierra):
                depth -= 1
                if depth == 0:
                    self.adv(); return
            self.adv()

    def decl(self):
        mods: list[str] = []
        while self.cur.kind == "NAME" and self.cur.value in MODS:
            mods.append(self.adv().value)
        if self.cur.kind != "NAME":
            raise SintaxisDafny(f"declaración inesperada {self.cur.value!r} (línea {self.cur.line})")
        kw = self.cur.value
        if kw in ("function", "predicate") and not ({"least", "greatest"} & set(mods)):
            return self.function()
        if kw == "method":
            return self.method()
        self.adv()
        nombre = self.cur.value if self.cur.kind == "NAME" else ""
        self.saltar()
        if kw in ("function", "predicate"):
            kw = f"{mods[-1]} {kw}"
        return Other(kw, nombre)

    def function(self) -> Func:
        kw = self.adv().value
        if self.at("method"):
            self.adv()
        line = self.cur.line
        nombre = self.name()
        generic = self.genericos()
        params = self.params()
        retname = None
        if kw == "function":
            self.eat(":")
            if self.at("(") and self.peek().kind == "NAME" and self.peek(2).value == ":":
                self.adv(); retname = self.name(); self.eat(":"); ret = self.type(); self.eat(")")
            else:
                ret = self.type()
        else:
            ret = ("bool",)
        req, ens, _ = self.specs()
        body = None
        if self.at("{"):
            self.adv(); body = self.expr(); self.eat("}")
        return Func(nombre, params, ret, req, ens, body, kw, generic, retname, line)

    def method(self) -> Method:
        line = self.cur.line
        self.eat("method")
        nombre = self.name()
        generic = self.genericos()
        params = self.params()
        rets: list[Par] = []
        if self.at("returns"):
            self.adv(); rets = self.params()
        req, ens, modifies = self.specs()
        if self.at("{"):
            self.saltar_par("{", "}")
        return Method(nombre, params, rets, req, ens, modifies, generic, line)

    def genericos(self) -> bool:
        if not self.at("<"):
            return False
        self.saltar_par("<", ">")
        return True

    def params(self) -> list[Par]:
        self.eat("(")
        out: list[Par] = []
        while not self.at(")"):
            while self.cur.kind == "NAME" and self.cur.value in ("ghost", "nameonly"):
                self.adv()
            if self.cur.kind == "NAME" and self.peek().value == ":":
                n = self.name(); self.eat(":"); t = self.type()
            else:
                n, t = f"_{len(out)}", self.type()
            if self.at(":="):
                self.adv(); self.expr()
            out.append(Par(n, t))
            if self.at(","):
                self.adv()
            elif not self.at(")"):
                raise SintaxisDafny(f"esperaba ',' o ')', hay {self.cur.value!r} (línea {self.cur.line})")
        self.eat(")")
        return out

    def specs(self) -> tuple[list, list, bool]:
        req, ens, modifies = [], [], False
        while self.cur.kind == "NAME" and self.cur.value in SPECKW:
            k = self.adv().value
            if k == "requires":
                req.append(self.expr())
            elif k == "ensures":
                ens.append(self.expr())
            else:
                modifies = modifies or k == "modifies"
                self.lista_suelta()
        return req, ens, modifies

    def lista_suelta(self) -> None:
        """`decreases a, b`, `reads *`, `modifies this`: se parsea y se tira."""
        while True:
            if self.at("*"):
                self.adv()
            else:
                self.expr()
            if self.at(","):
                self.adv(); continue
            break

    # ---- tipos ----
    def type(self) -> tuple:
        t = self.cur
        if t.kind == "SYM" and t.value == "(":
            self.adv()
            ts = [self.type()]
            while self.at(","):
                self.adv(); ts.append(self.type())
            self.eat(")")
            base = ts[0] if len(ts) == 1 else ("tuple", *ts)
        elif t.kind == "NAME":
            v = self.adv().value
            if v in ("seq", "set", "iset", "multiset", "array", "array2", "array3", "map", "imap"):
                base = (v, *self.args_tipo())
            elif v in ("int", "nat", "bool", "real", "char", "string", "ORDINAL", "object"):
                base = (v,)
            elif re.fullmatch(r"bv\d+", v):
                base = ("bv",)
            else:
                args = self.args_tipo()
                while self.at("."):
                    self.adv(); v += "." + self.name()
                base = ("name", v, tuple(args))
        else:
            raise SintaxisDafny(f"esperaba un tipo, hay {t.value or 'fin'!r} (línea {t.line})")
        if self.at("->") or self.at("~>"):
            self.adv()
            return ("fn", base, self.type())
        return base

    def args_tipo(self) -> list:
        if not self.at("<"):
            return []
        self.adv()
        out = [self.type()]
        while self.at(","):
            self.adv(); out.append(self.type())
        self.eat(">")
        return out

    # ---- expresiones ----
    def expr(self):
        l = self.implica()
        while self.at("<==>"):
            self.adv(); l = DBin("<==>", l, self.implica())
        return l

    def implica(self):
        l = self.or_()
        if self.at("==>"):
            self.adv(); return DBin("==>", l, self.implica())
        while self.at("<=="):
            self.adv(); l = DBin("<==", l, self.or_())
        return l

    def or_(self):
        if self.at("||"):
            self.adv()
        l = self.and_()
        while self.at("||"):
            self.adv(); l = DBin("||", l, self.and_())
        return l

    def and_(self):
        if self.at("&&"):
            self.adv()
        l = self.cmp()
        while self.at("&&"):
            self.adv(); l = DBin("&&", l, self.cmp())
        return l

    def cmp(self):
        l = self.arit()
        partes = []
        while (self.cur.kind == "SYM" and self.cur.value in CMP) or (self.cur.kind == "NAME" and self.cur.value == "in"):
            op = self.adv().value
            partes.append((op, self.arit()))
        if not partes:
            return l
        out, izq = None, l
        for op, der in partes:  # `a <= b < c` -> `a <= b && b < c`
            c = DBin(op, izq, der)
            out = c if out is None else DBin("&&", out, c)
            izq = der
        return out

    def arit(self):
        l = self.term()
        while self.at("+") or self.at("-"):
            op = self.adv().value; l = DBin(op, l, self.term())
        return l

    def term(self):
        l = self.unario()
        while self.at("*") or self.at("/") or self.at("%"):
            op = self.adv().value; l = DBin(op, l, self.unario())
        return l

    def unario(self):
        if self.at("-"):
            self.adv(); return DUn("-", self.unario())
        if self.at("!"):
            self.adv(); return DUn("!", self.unario())
        return self.postfijo()

    def postfijo(self):
        e = self.primario()
        while True:
            if self.at("("):
                args = self.argumentos()
                e = DCall(e.n, args) if isinstance(e, DName) else DUnsup("llamada a una expresión")
            elif self.at("["):
                self.adv()
                if self.at(".."):
                    self.adv(); hi = None if self.at("]") else self.expr(); self.eat("]"); e = DSlice(e, None, hi)
                else:
                    i = self.expr()
                    if self.at(".."):
                        self.adv(); hi = None if self.at("]") else self.expr(); self.eat("]"); e = DSlice(e, i, hi)
                    elif self.at(":="):
                        self.adv(); self.expr(); self.eat("]"); e = DUnsup("actualización s[i := v]")
                    elif self.at(","):
                        while not self.at("]") and self.cur.kind != "EOF":
                            self.adv()
                        self.eat("]"); e = DUnsup("índice múltiple")
                    else:
                        self.eat("]"); e = DIndex(e, i)
            elif self.at("."):
                self.adv()
                if self.cur.kind == "INT":  # proyección de tupla `p.0`
                    self.adv(); e = DUnsup("tupla"); continue
                m = self.name()
                if self.at("("):
                    self.argumentos()
                e = DUnsup(f"miembro .{m}")
            elif self.at("as"):
                self.adv(); e = DAs(e, self.type())
            elif self.at("is"):
                self.adv(); self.type(); e = DUnsup("is")
            else:
                return e

    def argumentos(self) -> list:
        self.eat("(")
        out = []
        self.en_args += 1
        try:
            while not self.at(")"):
                out.append(self.expr())
                if self.at(","):
                    self.adv()
                elif not self.at(")"):
                    raise SintaxisDafny(f"esperaba ',' o ')', hay {self.cur.value!r} (línea {self.cur.line})")
        finally:
            self.en_args -= 1
        self.eat(")")
        return out

    def primario(self):
        t = self.cur
        if t.kind == "INT":
            self.adv(); return DInt(int(t.value))
        if t.kind == "REAL":
            self.adv(); return DUnsup("literal real")
        if t.kind == "STR":
            self.adv(); return DUnsup("literal de texto")
        if t.kind == "CHAR":
            self.adv(); return DUnsup("literal de carácter")
        if t.kind == "SYM":
            if t.value == "(":
                self.adv()
                if self.at(")"):
                    self.adv()
                    if self.at("=>"):
                        self.adv(); self.expr()
                    return DUnsup("tupla vacía o lambda")
                e = self.expr()
                if self.at(","):
                    while self.at(","):
                        self.adv(); self.expr()
                    self.eat(")")
                    if self.at("=>"):
                        self.adv(); self.expr(); return DUnsup("lambda")
                    return DUnsup("tupla")
                self.eat(")")
                if self.at("=>"):
                    self.adv(); self.expr(); return DUnsup("lambda")
                return e
            if t.value == "[":
                self.adv(); items = []
                while not self.at("]"):
                    items.append(self.expr())
                    if self.at(","):
                        self.adv()
                    elif not self.at("]"):
                        raise SintaxisDafny(f"esperaba ',' o ']', hay {self.cur.value!r} (línea {self.cur.line})")
                self.eat("]"); return DList(items)
            if t.value == "{":
                self.saltar_par("{", "}"); return DUnsup("literal de conjunto o mapa")
            if t.value == "|":
                self.adv(); e = self.expr(); self.eat("|"); return DCard(e)
            raise SintaxisDafny(f"expresión inesperada {t.value!r} (línea {t.line})")
        v = t.value
        if v == "true":
            self.adv(); return DBool(True)
        if v == "false":
            self.adv(); return DBool(False)
        if v in ("null", "this"):
            self.adv(); return DUnsup(v)
        if v == "if":
            self.adv(); c = self.expr(); self.eat("then"); a = self.expr(); self.eat("else"); b = self.expr()
            return DIf(c, a, b)
        if v in ("forall", "exists"):
            return self.cuantificador()
        if v == "var":
            return self.let()
        if v in ("assert", "assume"):
            self.adv(); self.expr()
            if self.at("by"):
                self.adv(); self.saltar_par("{", "}")
            self.eat(";"); return self.expr()
        if v == "match":
            self.adv(); self.expr()
            if not self.at("{"):
                raise SintaxisDafny(f"match sin llaves (línea {t.line})")
            self.saltar_par("{", "}"); return DUnsup("match")
        if v in ("old", "fresh", "unchanged", "allocated"):
            self.adv(); self.argumentos(); return DUnsup(v)
        if v in ("set", "iset", "map", "imap", "multiset", "seq"):
            self.adv()
            if self.at("<"):
                self.args_tipo()
            if self.at("("):
                self.argumentos(); return DUnsup(f"{v}(...)")
            if self.at("{"):
                self.saltar_par("{", "}"); return DUnsup(f"literal {v}")
            if self.at("["):
                self.saltar_par("[", "]"); return DUnsup(f"literal {v}")
            self.comprension(); return DUnsup(f"comprensión {v}")
        if t.kind == "EOF":
            raise SintaxisDafny(f"expresión incompleta (línea {t.line})")
        self.adv()
        if self.en_args and self.at("requires"):  # `seq(n, i requires P => e)`: lambda con precondición
            self.adv(); self.expr(); self.eat("=>"); self.expr(); return DUnsup("lambda")
        if self.at("=>"):
            self.adv(); self.expr(); return DUnsup("lambda")
        return DName(v)

    def binders(self) -> list:
        out = []
        while True:
            n = self.name(); typ = None; dom = None
            if self.at(":"):
                self.adv(); typ = self.type()
            if self.at("<") and self.peek().kind == "SYM" and self.peek().value == "-":
                self.adv(); self.adv(); dom = self.arit()
            out.append((n, typ, dom))
            if self.at(","):
                self.adv(); continue
            return out

    def cuantificador(self) -> DQuant:
        kind = self.adv().value
        bs = self.binders()
        rng = None
        if self.at("|"):
            self.adv(); rng = self.expr()
        self.eat("::")
        return DQuant(kind, bs, rng, self.expr())

    def comprension(self) -> None:
        self.binders()
        if self.at("|"):
            self.adv(); self.expr()
        if self.at("::"):
            self.adv(); self.expr()

    def let(self):
        self.eat("var")
        if self.at("("):
            self.saltar_par("(", ")")
            if self.at(":="):
                self.adv(); self.expr()
            self.eat(";"); self.expr(); return DUnsup("var con patrón")
        nombres = [self.name()]
        if self.at(":"):
            self.adv(); self.type()
        while self.at(","):
            self.adv(); nombres.append(self.name())
            if self.at(":"):
                self.adv(); self.type()
        if self.at(":|"):
            self.adv(); self.expr(); self.eat(";"); self.expr(); return DUnsup("var :| (elección)")
        self.eat(":=")
        inits = [self.expr()]
        while self.at(","):
            self.adv(); inits.append(self.expr())
        self.eat(";")
        body = self.expr()
        if len(inits) != len(nombres):
            return DUnsup("var múltiple desigual")
        for n, init in reversed(list(zip(nombres, inits))):
            body = DLet(n, init, body)
        return body


# ---------- la spec: secciones y declaraciones ----------

@dataclass
class Spec:
    id: str
    source: str
    source_id: str
    texto: str
    funcs: dict[str, Func]
    metodo: Method | None
    otros: list[Other]
    metodos: list[str]        # métodos del preámbulo (con cuerpo), ignorados
    error_spec: str | None    # la sección <vc-spec> no parsea


def secciones(texto: str) -> tuple[str, str]:
    """(resto, spec): el texto sin `<vc-code>` ni marcas, y la sección `<vc-spec>` aparte."""
    m = re.search(r"//\s*<vc-spec>(.*?)//\s*</vc-spec>", texto, re.S)
    spec = m.group(1) if m else ""
    resto = re.sub(r"//\s*<vc-code>.*?//\s*</vc-code>", "", texto, flags=re.S)
    resto = re.sub(r"//\s*<vc-spec>.*?//\s*</vc-spec>", "", resto, flags=re.S)
    resto = re.sub(r"//\s*</?vc-\w+>", "", resto)
    return resto, spec


def leer_spec(id_: str, texto: str, meta: dict | None = None) -> Spec:
    meta = meta or {}
    resto, spec = secciones(texto)
    funcs: dict[str, Func] = {}
    otros: list[Other] = []
    metodos: list[str] = []
    try:
        for d in Parser(lex(resto)).decls():
            if isinstance(d, Func):
                funcs.setdefault(d.name, d)
            elif isinstance(d, Method):
                metodos.append(d.name)
            else:
                otros.append(d)
    except SintaxisDafny as e:
        otros.append(Other("sintaxis", str(e)))
    metodo, error = None, None
    try:
        ds = Parser(lex(spec)).decls()
        metodo = next((d for d in ds if isinstance(d, Method)), None)
        if metodo is None and spec.strip():
            fallo = next((d for d in ds if isinstance(d, Other) and d.kind == "sintaxis"), None)
            error = f"sintaxis en <vc-spec>: {fallo.name}" if fallo else "la sección <vc-spec> no tiene un método"
    except SintaxisDafny as e:
        error = f"sintaxis en <vc-spec>: {e}"
    return Spec(id_, meta.get("source", ""), meta.get("source-id", ""), texto, funcs, metodo, otros, metodos, error)


# ---------- traducción ----------

def tipo_sello(t: tuple) -> Type | str:
    """El tipo de Sello, o el motivo por el que no lo hay."""
    k = t[0]
    if k in ("int", "nat"):
        return INT
    if k == "bool":
        return BOOL
    if k == "seq":
        inner = tipo_sello(t[1]) if len(t) > 1 else "tipo: seq sin argumento"
        return inner if isinstance(inner, str) else TList(inner)
    if k in ("array", "array2", "array3"):
        return "tipo: array"
    if k in ("set", "iset"):
        return "tipo: set"
    if k in ("map", "imap"):
        return "tipo: map"
    if k in ("real", "string", "char", "multiset", "tuple", "bv"):
        return f"tipo: {k}"
    if k == "name":
        return "tipo: datatype u otro"
    return f"tipo: {tipo_texto(t)}"


def sanear(n: str) -> str:
    n = re.sub(r"[^A-Za-z0-9_]", "_", n)
    if not n or not n[0].isalpha():
        n = "v" + n
    if n in RESERVADOS:
        n += "_"
    return n


# Pequeños a propósito: `ensures result == <cuerpo>` en un helper recursivo se reevalúa en cada
# nivel (el coste se dobla por nivel: power(2, 100) no termina) y un helper puede recorrer los
# dos enteros a la vez.
CANDIDATOS_INT = [0, 1, 2, 3, 5, 7, 10, 12, -1, -5]
CANDIDATOS_LISTA = [[], [1], [3, 1, 2], [2, 2, 5], [-1, 4, 0], [1, 2, 3, 4, 5]]


def candidatos(t: Type) -> list:
    if isinstance(t, TInt):
        return CANDIDATOS_INT
    if isinstance(t, TBool):
        return [True, False]
    if isinstance(t, TList):
        if isinstance(t.elem, TInt):
            return CANDIDATOS_LISTA
        if isinstance(t.elem, TBool):
            return [[], [True], [True, False], [False, False, True]]
        return [[], [[1]], [[1, 2], []], [[3], [4, 5]]]
    return []


def tautologia(params: list[Param]) -> Expr:
    """Sello exige `requires` y rechaza el literal `true` (E102): la cláusula que no asume nada."""
    for p in params:
        if isinstance(p.type, TList):
            return Binary(">=", Call("len", [Name(p.name)]), IntLit(0))
    if params:
        return Binary("==", Name(params[0].name), Name(params[0].name))
    return Binary("==", IntLit(1), IntLit(1))


@dataclass
class Tarea:
    id: str
    source: str
    source_id: str
    fn: str                 # nombre Sello de la principal
    sello: str              # firma, como en las otras baterías
    esqueleto: str          # programa Sello completo con cuerpo y ejemplo de relleno en la principal
    helpers: list[str]
    notas: list[str]
    dafny: str

    def to_dict(self) -> dict:
        return {"id": self.id, "source": self.source, "source_id": self.source_id, "fn": self.fn, "sello": self.sello,
                "helpers": self.helpers, "notas": self.notas, "esqueleto": self.esqueleto, "dafny": self.dafny}

    @staticmethod
    def from_dict(d: dict) -> Tarea:
        return Tarea(d["id"], d["source"], d["source_id"], d["fn"], d["sello"], d["esqueleto"], d["helpers"], d["notas"], d["dafny"])


def contrato(tarea: Tarea) -> ct.Contrato:
    """El contrato congelado (helpers completos, principal sin cuerpo ni ejemplos)."""
    prog = parse(tarea.esqueleto)
    principal = next(f for f in prog.fns if f.name == tarea.fn)
    return ct.Contrato(principal, [f for f in prog.fns if f.name != tarea.fn], ejemplos_libres=True)


class Traductor:
    def __init__(self, spec: Spec) -> None:
        self.spec = spec
        self.funcs = dict(spec.funcs)
        # Dafny no trae `abs`, `min` ni `max`, pero algunas specs los usan sin definirlos (en el
        # benchmark los define quien resuelve): se suponen con su definición de siempre.
        self.supuestas: set[str] = set()
        a, b = DName("a"), DName("b")
        for nombre, params, cuerpo in (
                ("abs", ["a"], DIf(DBin(">=", a, DInt(0)), a, DUn("-", a))),
                ("min", ["a", "b"], DIf(DBin("<=", a, b), a, b)),
                ("max", ["a", "b"], DIf(DBin(">=", a, b), a, b))):
            if nombre not in self.funcs:
                self.funcs[nombre] = Func(nombre, [Par(x, ("int",)) for x in params], ("int",), [], [], cuerpo,
                                          "function", False, None, 0)
                self.supuestas.add(nombre)
        self.motivos: list[str] = []
        self.notas: set[str] = set()
        self.n = 0
        self.en_cuerpo = False
        grafo = {n: {c for c in self.llamadas_fn(f) if c in self.funcs} for n, f in self.funcs.items()}
        self.recursivas: set[str] = set()
        for comp in _sccs(grafo):
            if len(comp) > 1 or comp[0] in grafo[comp[0]]:
                self.recursivas |= set(comp)
        self.planas: dict[str, object] = {}
        self.nombres_fn: dict[str, str] = {}

    @staticmethod
    def llamadas_fn(f: Func) -> set[str]:
        out: set[str] = set()
        for e in f.requires + f.ensures + ([f.body] if f.body is not None else []):
            out |= llamadas(e)
        return out

    def motivo(self, m: str) -> None:
        if m not in self.motivos:
            self.motivos.append(m)

    def fresco(self, base: str, evitar: set[str]) -> str:
        while True:
            self.n += 1
            cand = f"{base}_{self.n}"
            if cand not in evitar:
                return cand

    def nombre_fn(self, dafny: str) -> str:
        if dafny not in self.nombres_fn:
            cand = sanear(dafny)
            while cand in self.nombres_fn.values():
                cand += "_"
            self.nombres_fn[dafny] = cand
        return self.nombres_fn[dafny]

    @staticmethod
    def nombre_var(dafny: str, env: dict) -> str:
        cand = sanear(dafny)
        usados = {v[0] for v in env.values()}
        while cand in usados:
            cand += "_"
        return cand

    # ---- aplanar: inlining de helpers no recursivos y de `var` ----
    def aplanar(self, e, prof: int = 0):
        if isinstance(e, DCall):
            args = [self.aplanar(a, prof) for a in e.args]
            f = self.funcs.get(e.f)
            if f is None or e.f in self.recursivas or f.body is None or f.generic:
                return DCall(e.f, args)
            if prof > 30:
                self.motivo("inlining demasiado profundo")
                return DCall(e.f, args)
            if len(args) != len(f.params):
                self.motivo(f"aridad de {e.f}")
                return DCall(e.f, args)
            if e.f in self.supuestas:
                self.notas.add(f"función supuesta: {e.f}")
            if e.f not in self.planas:
                self.planas[e.f] = self.aplanar(f.body, prof + 1)
            return self.subst(self.planas[e.f], {p.name: a for p, a in zip(f.params, args)})
        if isinstance(e, DLet):
            init = self.aplanar(e.init, prof)
            return self.subst(self.aplanar(e.body, prof), {e.n: init})
        return mapa(e, lambda c: self.aplanar(c, prof))

    def subst(self, e, m: dict):
        """`e[m]` sin captura: una variable ligada que choque con las libres de lo sustituido se renombra."""
        if not m:
            return e
        if isinstance(e, DName):
            return m.get(e.n, e)
        if isinstance(e, DQuant):
            fv: set[str] = set().union(*(libres(v) for v in m.values()))
            m2 = dict(m)
            ren: dict = {}
            bs = list(e.binders)
            for k, (n, t, d) in enumerate(bs):
                m2.pop(n, None)
                if n in fv:
                    nuevo = self.fresco(n, fv | libres(e) | set(m))
                    ren[n] = DName(nuevo)
                    bs[k] = (nuevo, t, d)
            rng, body = e.rng, e.body
            if ren:
                bs = [(n, t, None if d is None else self.subst(d, ren)) for n, t, d in bs]
                rng = None if rng is None else self.subst(rng, ren)
                body = self.subst(body, ren)
            bs = [(n, t, None if d is None else self.subst(d, m2)) for n, t, d in bs]
            return DQuant(e.kind, bs, None if rng is None else self.subst(rng, m2), self.subst(body, m2))
        if isinstance(e, DLet):
            init = self.subst(e.init, m)
            m2 = {k: v for k, v in m.items() if k != e.n}
            n, body = e.n, e.body
            fv = set().union(*(libres(v) for v in m2.values())) if m2 else set()
            if n in fv:
                nuevo = self.fresco(n, fv | libres(body) | set(m))
                body = self.subst(body, {n: DName(nuevo)})
                n = nuevo
            return DLet(n, init, self.subst(body, m2))
        return mapa(e, lambda c: self.subst(c, m))

    # ---- tipos de Dafny (inferencia mínima: para `+` y para los cuantificadores) ----
    def dtipo(self, e, env: dict) -> tuple:
        if isinstance(e, DInt): return ("int",)
        if isinstance(e, DBool): return ("bool",)
        if isinstance(e, DName): return env[e.n][1] if e.n in env else ("?",)
        if isinstance(e, DList): return ("seq", self.dtipo(e.items[0], env) if e.items else ("?",))
        if isinstance(e, DCall):
            f = self.funcs.get(e.f)
            return f.ret if f else ("?",)
        if isinstance(e, DUn): return ("bool",) if e.op == "!" else self.dtipo(e.e, env)
        if isinstance(e, DBin):
            if e.op in ("&&", "||", "==>", "<==", "<==>", "==", "!=", "<", "<=", ">", ">=", "in", "!in"):
                return ("bool",)
            l = self.dtipo(e.l, env)
            return l if l[0] != "?" else self.dtipo(e.r, env)
        if isinstance(e, DIf):
            a = self.dtipo(e.a, env)
            return a if a[0] != "?" else self.dtipo(e.b, env)
        if isinstance(e, DCard): return ("int",)
        if isinstance(e, DIndex):
            t = self.dtipo(e.e, env)
            return t[1] if t[0] in ("seq", "array") and len(t) > 1 else ("char",) if t[0] == "string" else ("?",)
        if isinstance(e, DSlice): return self.dtipo(e.e, env)
        if isinstance(e, DAs): return e.t
        if isinstance(e, DQuant): return ("bool",)
        if isinstance(e, DLet): return self.dtipo(e.body, {**env, e.n: ("", self.dtipo(e.init, env))})
        return ("?",)

    def motivo_tipo(self, t: tuple, donde: str) -> str:
        if t[0] == "?":
            return f"tipo desconocido en {donde}"
        r = tipo_sello(t)
        return r if isinstance(r, str) else f"tipo {tipo_texto(t)} en {donde}"

    def solo_contrato(self, palabra: str) -> None:
        if self.en_cuerpo:
            self.motivo(f"helper recursivo con `{palabra}` en el cuerpo")

    # ---- expresiones ----
    def expr(self, e, env: dict) -> Expr:
        if isinstance(e, DInt):
            return IntLit(e.v)
        if isinstance(e, DBool):
            return BoolLit(e.v)
        if isinstance(e, DName):
            if e.n in env:
                return Name(env[e.n][0])
            self.motivo(f"nombre sin definir: {e.n}")
            return IntLit(0)
        if isinstance(e, DList):
            return ListLit([self.expr(x, env) for x in e.items])
        if isinstance(e, DCall):
            args = [self.expr(a, env) for a in e.args]
            f = self.funcs.get(e.f)
            if f is not None and e.f in self.recursivas and f.body is not None and not f.generic:
                return Call(self.nombre_fn(e.f), args)
            if f is None:
                self.motivo(f"función sin definir: {e.f}")
            elif f.generic:
                self.motivo("genéricos")
            else:
                self.motivo(f"función sin cuerpo: {e.f}")
            return IntLit(0)
        if isinstance(e, DUn):
            return Unary("not" if e.op == "!" else "-", self.expr(e.e, env))
        if isinstance(e, DBin):
            return self.binaria(e, env)
        if isinstance(e, DIf):
            return If(self.expr(e.c, env), self.expr(e.a, env), self.expr(e.b, env))
        if isinstance(e, DCard):
            t = self.dtipo(e.e, env)
            if t[0] != "seq":
                self.motivo(self.motivo_tipo(t, "|·|"))
            self.solo_contrato("len")
            return Call("len", [self.expr(e.e, env)])
        if isinstance(e, DIndex):
            self.motivo("índice s[i]")
            self.expr(e.e, env); self.expr(e.i, env)
            return IntLit(0)
        if isinstance(e, DSlice):
            self.motivo("tramo s[i..j]")
            self.expr(e.e, env)
            return IntLit(0)
        if isinstance(e, DAs):
            if e.t[0] in ("int", "nat"):
                self.notas.add("as int")
                return self.expr(e.e, env)
            self.motivo(f"conversión as {tipo_texto(e.t)}")
            return IntLit(0)
        if isinstance(e, DQuant):
            return self.cuantificador(e, env)
        if isinstance(e, DLet):
            self.motivo("var (let) sin aplanar")
            return IntLit(0)
        if isinstance(e, DUnsup):
            self.motivo(e.what)
            return IntLit(0)
        raise TypeError(f"nodo desconocido: {e!r}")

    def binaria(self, e: DBin, env: dict) -> Expr:
        op = e.op
        if op in ("&&", "||"):
            return Binary("and" if op == "&&" else "or", self.expr(e.l, env), self.expr(e.r, env))
        if op == "==>":
            return Binary("or", Unary("not", self.expr(e.l, env)), self.expr(e.r, env))
        if op == "<==":
            return Binary("or", Unary("not", self.expr(e.r, env)), self.expr(e.l, env))
        if op == "<==>":
            return Binary("==", self.expr(e.l, env), self.expr(e.r, env))
        if op in ("in", "!in"):
            t = self.dtipo(e.r, env)
            if t[0] != "seq":
                self.motivo(self.motivo_tipo(t, "in"))
            self.solo_contrato("contains")
            c = Call("contains", [self.expr(e.r, env), self.expr(e.l, env)])
            return c if op == "in" else Unary("not", c)
        tl, tr = self.dtipo(e.l, env), self.dtipo(e.r, env)
        for t in (tl, tr):
            if t[0] not in ("int", "nat", "bool", "seq", "?"):
                self.motivo(self.motivo_tipo(t, op))
        l, r = self.expr(e.l, env), self.expr(e.r, env)
        if op in ("==", "!="):
            return Binary(op, l, r)
        if op in ("<", "<=", ">", ">="):
            if tl[0] == "seq" or tr[0] == "seq":
                self.motivo("comparación de secuencias")
            return Binary(op, l, r)
        if op == "+":
            return Binary("++" if tl[0] == "seq" or tr[0] == "seq" else "+", l, r)
        if op in ("-", "*"):
            return Binary(op, l, r)
        if op in ("/", "%"):
            if not (isinstance(e.r, DInt) and e.r.v > 0):
                self.notas.add("div")
            return Binary(op, l, r)
        self.motivo(f"operador {op}")
        return IntLit(0)

    def cuantificador(self, q: DQuant, env: dict) -> Expr:
        """Solo las formas con dominio en una secuencia: `forall x :: x in s ==> P`, `exists x ::
        x in s && P`, `forall x | x in s :: P`, `forall x <- s :: P`, con varias variables anidadas."""
        self.solo_contrato(q.kind)
        forall = q.kind == "forall"
        premisas = conjuntos(q.rng) if q.rng is not None else []
        cuerpo = q.body
        if forall:
            if isinstance(cuerpo, DBin) and cuerpo.op == "==>":
                premisas = premisas + conjuntos(cuerpo.l)
                cuerpo = cuerpo.r
        else:
            premisas = premisas + conjuntos(cuerpo)
            cuerpo = None
        ligadas = {b for b, _, _ in q.binders}
        sujetos: list[tuple[str, object]] = []
        for n, t, d in q.binders:
            if d is not None:
                sujetos.append((n, d)); continue
            for k, p in enumerate(premisas):
                if (isinstance(p, DBin) and p.op == "in" and isinstance(p.l, DName) and p.l.n == n
                        and not (libres(p.r) & ligadas)):
                    sujetos.append((n, p.r)); premisas.pop(k); break
            else:
                acotado = any(isinstance(p, DBin) and p.op in ("<", "<=", ">", ">=") and n in libres(p) for p in premisas)
                self.motivo("cuantificador sobre enteros" if acotado or (t and t[0] in ("int", "nat")) else "cuantificador sin dominio")
                return BoolLit(True)
        if forall:
            resto = conjuncion(premisas)
            cuerpo_d = cuerpo if resto is None else DBin("==>", resto, cuerpo)
        else:
            cuerpo_d = conjuncion(premisas + ([cuerpo] if cuerpo is not None else [])) or DBool(True)
        env2 = dict(env)
        for n, s in sujetos:
            st = self.dtipo(s, env)
            if st[0] != "seq":
                self.motivo(self.motivo_tipo(st, "in"))
            env2[n] = (self.nombre_var(n, env2), st[1] if st[0] == "seq" and len(st) > 1 else ("?",))
        out = self.expr(cuerpo_d, env2)
        for n, s in reversed(sujetos):
            out = Quant(q.kind, env2[n][0], self.expr(s, env), out)
        return out

    # ---- cláusulas ----
    def clausulas(self, exprs: list, env: dict) -> list[Expr]:
        out: list[Expr] = []
        for e in exprs:
            for c in conjuntos(self.aplanar(e)):
                if isinstance(c, DBool) and c.v:
                    self.notas.add("cláusula `true` eliminada")
                    continue
                out.append(self.expr(c, env))
        return out

    def nat_de(self, nombre: str, t: tuple, prof: int = 0) -> Expr | None:
        """`n >= 0` para un `nat`; `forall x in s: x >= 0` para `seq<nat>`, anidado si hace falta."""
        if t[0] == "nat":
            return Binary(">=", Name(nombre), IntLit(0))
        if t[0] == "seq" and len(t) > 1:
            var = f"x{prof}" if prof else "x"
            inner = self.nat_de(var, t[1], prof + 1)
            return None if inner is None else Quant("forall", var, Name(nombre), inner)
        return None

    def params_sello(self, params: list[Par], env: dict) -> list[Param]:
        out: list[Param] = []
        for p in params:
            t = tipo_sello(p.type)
            if isinstance(t, str):
                self.motivo(t); t = INT
            sn = self.nombre_var(p.name, env)
            env[p.name] = (sn, p.type)
            out.append(Param(sn, t))
        return out

    def requires_de(self, params: list[Par], sparams: list[Param], exprs: list, env: dict) -> list[Expr]:
        out: list[Expr] = []
        for p, sp in zip(params, sparams):
            c = self.nat_de(sp.name, p.type)
            if c is not None:
                self.notas.add("nat"); out.append(c)
        out += self.clausulas(exprs, env)
        if not out:
            self.notas.add("requires vacío")
            out.append(tautologia(sparams))
        return out

    def helper(self, f: Func) -> Fn:
        env: dict = {}
        params = self.params_sello(f.params, env)
        ret = tipo_sello(f.ret)
        if isinstance(ret, str):
            self.motivo(ret); ret = INT
        cuerpo_d = self.aplanar(f.body)
        self.en_cuerpo = True
        try:
            body = self.expr(cuerpo_d, env)
        finally:
            self.en_cuerpo = False
        requires = self.requires_de(f.params, params, f.requires, env)
        renv = dict(env)
        renv["$result"] = ("result", f.ret)
        if f.retname:
            renv[f.retname] = ("result", f.ret)
        yo = [DName(p.name) for p in f.params]

        def resultado(e):  # `f(params)` en el ensures de Dafny es el resultado
            if isinstance(e, DCall) and e.f == f.name and e.args == yo:
                return DName("$result")
            return mapa(e, resultado)

        ensures = [Binary("==", Name("result"), self.expr(cuerpo_d, env))]
        ensures += self.clausulas([resultado(e) for e in f.ensures], renv)
        c = self.nat_de("result", f.ret)
        if c is not None:
            self.notas.add("nat"); ensures.append(c)
        return Fn(self.nombre_fn(f.name), params, ret, requires, ensures, "pure", [], body)

    def principal(self) -> Fn | None:
        m = self.spec.metodo
        if m is None:
            self.motivo(self.spec.error_spec or "sin método")
            return None
        if m.generic:
            self.motivo("genéricos")
        if m.modifies:
            self.motivo("modifies")
        if not m.returns:
            self.motivo("sin valor de retorno")
        elif len(m.returns) > 1:
            self.motivo("varios valores de retorno")
        if not m.ensures:
            self.motivo("sin ensures")
        env: dict = {}
        params = self.params_sello(m.params, env)
        ret_d = m.returns[0].type if m.returns else ("int",)
        ret = tipo_sello(ret_d)
        if isinstance(ret, str):
            self.motivo(ret); ret = INT
        requires = self.requires_de(m.params, params, m.requires, env)
        renv = dict(env)
        for r in m.returns:  # varios valores de retorno ya no caben: solo evita motivos de más
            renv[r.name] = ("result", r.type)
        ensures = self.clausulas(m.ensures, renv)
        c = self.nat_de("result", ret_d)
        if c is not None:
            self.notas.add("nat"); ensures.append(c)
        if not ensures and m.ensures:
            self.motivo("sin ensures")
        relleno = {INT: IntLit(0), BOOL: BoolLit(True)}
        cuerpo = relleno.get(ret, ListLit([]))
        args = [relleno.get(p.type, ListLit([])) for p in params]
        nombre = self.nombre_fn(m.name)
        ejemplo = Binary("==", Call(nombre, args), cuerpo)
        return Fn(nombre, params, ret, requires, ensures, "pure", [ejemplo], cuerpo)

    def necesarias(self, principal: Fn) -> list[Func]:
        """Los helpers recursivos que aparecen en el contrato (y en los de ellos), en el orden del preámbulo."""
        def nombres(fns: list[Fn]) -> set[str]:
            out: set[str] = set()
            for fn in fns:
                for e in fn.requires + fn.ensures + [fn.body]:
                    out |= {c.name for c in llamadas_sello(e)}
            return out
        inv = {v: k for k, v in self.nombres_fn.items()}
        vistos: set[str] = set()
        pendientes = {inv[n] for n in nombres([principal]) if n in inv}
        traducidos: dict[str, Fn] = {}
        while pendientes:
            d = pendientes.pop()
            if d in vistos:
                continue
            vistos.add(d)
            traducidos[d] = self.helper(self.funcs[d])
            inv = {v: k for k, v in self.nombres_fn.items()}
            pendientes |= {inv[n] for n in nombres([traducidos[d]]) if n in inv} - vistos
        return [self.funcs[n] for n in self.funcs if n in traducidos], traducidos

    def ejemplos(self, prog: Program, fn: Fn, segundos: float = 3.0) -> list[Expr]:
        """Dos `example` con resultados distintos, sobre entradas pequeñas que cumplan el
        `requires`; con reloj (`SIGALRM`, solo en el hilo principal) por si una entrada no acaba."""
        interp = Interpreter(prog)
        out: list[Expr] = []
        valores: set[str] = set()
        cands = [candidatos(p.type) for p in fn.params]
        if not cands or any(not c for c in cands):
            return out
        fin = time.monotonic() + segundos
        con_reloj = threading.current_thread() is threading.main_thread()

        class Tarde(Exception):
            pass

        def alarma(*_):
            raise Tarde()

        if con_reloj:
            anterior = signal.signal(signal.SIGALRM, alarma)
        try:
            for combo in itertools.islice(itertools.product(*cands), 600):
                if time.monotonic() > fin:
                    break
                if con_reloj:
                    signal.setitimer(signal.ITIMER_REAL, max(0.05, fin - time.monotonic()))
                try:
                    v = interp.call(fn.name, list(combo))
                except (SelloError, RecursionError):
                    continue
                except Tarde:
                    break
                finally:
                    if con_reloj:
                        signal.setitimer(signal.ITIMER_REAL, 0)
                if fmt(v) in valores:
                    continue
                valores.add(fmt(v))
                out.append(parse_expr(f"{fn.name}(" + ", ".join(fmt(a) for a in combo) + f") == {fmt(v)}"))
                if len(out) == 2:
                    break
        finally:
            if con_reloj:
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, anterior)
        return out

    def traducir(self) -> Tarea | None:
        s = self.spec
        if s.otros and any(o.kind == "lemma" for o in s.otros):
            self.notas.add("lema ignorado")
        if s.metodos:
            self.notas.add("método del preámbulo ignorado")
        principal = self.principal()
        if principal is None:
            return None
        orden, traducidos = self.necesarias(principal)
        helpers = [traducidos[f.name] for f in orden]
        if self.motivos:
            return None
        for h in helpers:  # de relleno hasta calcularlos: el checker exige uno
            h.examples = [BoolLit(True)]
        prog = Program(helpers + [principal])
        try:
            texto = "\n\n".join(unparse_fn(f) for f in prog.fns)
            prog = parse(texto)
            Checker(prog).check()
        except SelloError as e:
            self.motivo(f"traducción inválida: {e.code} {e.detail[:100]}")
            return None
        for fn in prog.fns[:-1]:
            fn.examples = self.ejemplos(prog, fn)
            if not fn.examples:
                self.motivo(f"sin ejemplo para el helper {fn.name}")
                return None
        texto = "\n\n".join(unparse_fn(f) for f in prog.fns)
        try:
            Checker(parse(texto)).check()
        except SelloError as e:
            self.motivo(f"traducción inválida: {e.code} {e.detail[:100]}")
            return None
        m = s.metodo
        firma = f"{principal.name}(" + ", ".join(f"{p.name}: {p.type}" for p in principal.params) + f") -> {principal.ret}"
        return Tarea(s.id, s.source, s.source_id, principal.name, firma, texto,
                     [f.name for f in prog.fns[:-1]], sorted(self.notas), s.texto)


def llamadas_sello(e: Expr) -> list[Call]:
    from sello.nodes import children
    out = [e] if isinstance(e, Call) and e.name not in BUILTINS else []
    for c in children(e):
        out += llamadas_sello(c)
    return out


def traducir(id_: str, texto: str, meta: dict | None = None) -> tuple[Tarea | None, list[str], list[str]]:
    """(tarea o None, motivos por los que no cabe, notas)."""
    tr = Traductor(leer_spec(id_, texto, meta))
    tarea = tr.traducir()
    return tarea, tr.motivos, sorted(tr.notas)


# ---------- cobertura ----------

def metadatos() -> dict[str, dict]:
    if not CSV.exists():
        raise SystemExit(f"falta {CSV}: uv run python bench/vericoding/bajar.py")
    return {r["id"]: r for r in csv.DictReader(CSV.open())}


def agrupar(motivo: str) -> str:
    """Familias de motivos, para la tabla."""
    for pref, fam in (("tipo:", "tipo no soportado"), ("función sin definir", "función sin definir"),
                      ("función sin cuerpo", "función sin cuerpo"), ("nombre sin definir", "nombre sin definir"),
                      ("traducción inválida", "traducción inválida"), ("sin ejemplo", "sin ejemplo para un helper"),
                      ("helper recursivo", "helper recursivo con vocabulario de contrato"),
                      ("tipo desconocido", "tipo desconocido"), ("literal", "literal real/texto/carácter"),
                      ("comprensión", "comprensión set/map/seq"), ("miembro", "miembro .x"),
                      ("esperaba", "sintaxis Dafny no cubierta"), ("carácter", "sintaxis Dafny no cubierta"),
                      ("la sección", "sintaxis Dafny no cubierta"), ("sintaxis en", "sintaxis Dafny no cubierta"), ("match", "match"), ("tipo ", "tipo no soportado")):
        if motivo.startswith(pref):
            return fam
    return motivo


def resumen(filas: list[dict], when: str) -> str:
    fuentes = [f for f in FUENTES if any(r["source"] == f for r in filas)]
    out = [f"# Traducción Dafny -> Sello {when}", "",
           "Qué cabe en Sello tal cual de las specs Dafny del benchmark de vericoding (sin `qa-issue`). "
           "Una tarea cabe si su método tiene un valor de retorno y `ensures`, todo es `int`/`nat`/`bool`/`seq`, "
           "y las cláusulas (con los helpers inlineados) se dicen con el vocabulario de contratos de Sello.", "",
           "| | " + " | ".join(fuentes) + " | total |", "|---|" + "---|" * (len(fuentes) + 1)]

    def fila(label, f):
        out.append(f"| {label} | " + " | ".join(f([r for r in filas if r["source"] == s]) for s in fuentes)
                   + f" | {f(filas)} |")
    fila("specs", lambda rs: str(len(rs)))
    fila("**caben**", lambda rs: f"**{sum(r['cabe'] for r in rs)}** ({100 * sum(r['cabe'] for r in rs) / max(1, len(rs)):.0f} %)")
    fila("· con helpers recursivos congelados", lambda rs: str(sum(1 for r in rs if r["cabe"] and r["helpers"])))
    for nota in sorted({n for r in filas if r["cabe"] for n in r["notas"]}):
        fila(f"· nota `{nota}`", lambda rs, nota=nota: str(sum(1 for r in rs if r["cabe"] and nota in r["notas"])))
    fila("longitud mediana del contrato (caracteres)", lambda rs: str(sorted(r["longitud"] for r in rs if r["cabe"])[len([r for r in rs if r["cabe"]]) // 2]) if any(r["cabe"] for r in rs) else "-")
    fila("longitud máxima", lambda rs: str(max((r["longitud"] for r in rs if r["cabe"]), default=0)))

    no = [r for r in filas if not r["cabe"]]
    familias: dict[str, int] = {}
    primeras: dict[str, int] = {}
    for r in no:
        fams = []
        for m in r["motivos"]:
            fam = agrupar(m)
            if fam not in fams:
                fams.append(fam)
        for fam in fams:
            familias[fam] = familias.get(fam, 0) + 1
        if fams:
            primeras[fams[0]] = primeras.get(fams[0], 0) + 1
    out += ["", "## Por qué no caben las demás", "",
            f"{len(no)} specs. Cada una puede tener varios motivos: `en alguna` cuenta la spec si el motivo aparece; "
            "`el primero` solo el primero que encuentra el traductor (cabecera antes que cláusulas).", "",
            "| motivo | en alguna | el primero |", "|---|---|---|"]
    for fam, c in sorted(familias.items(), key=lambda kv: -kv[1]):
        out.append(f"| {fam} | {c} | {primeras.get(fam, 0)} |")
    detalle: dict[str, int] = {}
    for r in no:
        for m in r["motivos"]:
            if agrupar(m) == "tipo no soportado":
                detalle[m] = detalle.get(m, 0) + 1
    if detalle:
        out += ["", "Tipos no soportados (specs en las que aparece):", ""]
        out += [f"- {m}: {c}" for m, c in sorted(detalle.items(), key=lambda kv: -kv[1])]
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*", help="ids concretos (por defecto, todas las Dafny sin qa-issue de la caché)")
    ap.add_argument("--ver", action="store_true", help="imprime el contrato (o los motivos) de cada id")
    ap.add_argument("--todas", action="store_true", help="también las specs con qa-issue")
    ap.add_argument("--sin-escribir", action="store_true", help="no toca tareas/ ni resultados/")
    args = ap.parse_args()
    meta = metadatos()
    ids = args.ids or sorted(i for i, r in meta.items() if r["language"] == "dafny" and (args.todas or r["qa-issue"] == "0"))
    filas: list[dict] = []
    tareas: list[Tarea] = []
    for id_ in ids:
        p = SPECS / f"{id_}_specs.dfy"
        if not p.exists():
            print(f"  {id_}: no está en la caché (bajar.py)", file=sys.stderr)
            continue
        tarea, motivos, notas = traducir(id_, p.read_text(), meta.get(id_))
        longitud = len(contrato(tarea).texto) if tarea else 0
        filas.append({"id": id_, "source": meta.get(id_, {}).get("source", ""), "cabe": tarea is not None,
                      "motivos": motivos, "notas": notas, "helpers": tarea.helpers if tarea else [], "longitud": longitud})
        if tarea:
            tareas.append(tarea)
        if args.ver:
            print(f"===== {id_} ({meta.get(id_, {}).get('source', '')}) =====")
            if tarea:
                print(contrato(tarea).texto)
                print(f"-- notas: {', '.join(notas) or '-'}")
            else:
                print("no cabe: " + "; ".join(motivos))
                if notas:
                    print(f"-- notas: {', '.join(notas)}")
            print()
    when = dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    md = resumen(filas, when)
    print(md)
    if args.sin_escribir or args.ids:
        return 0
    TAREAS.mkdir(exist_ok=True)
    for viejo in TAREAS.glob("*.json"):
        viejo.unlink()
    for t in tareas:
        (TAREAS / f"{t.id}.json").write_text(json.dumps(t.to_dict(), ensure_ascii=False, indent=1) + "\n")
    RESULTADOS.mkdir(exist_ok=True)
    (RESULTADOS / f"vericoding-traduccion-{when}.md").write_text(md)
    print(f"{len(tareas)} tareas en {TAREAS}; resumen en {RESULTADOS / f'vericoding-traduccion-{when}.md'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
