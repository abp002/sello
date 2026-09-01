"""AST de Sello: tipos, expresiones, patrones y funciones."""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------- tipos ----------

class Type:
    pass


@dataclass(frozen=True)
class TInt(Type):
    def __str__(self) -> str: return "Int"


@dataclass(frozen=True)
class TBool(Type):
    def __str__(self) -> str: return "Bool"


@dataclass(frozen=True)
class TText(Type):
    def __str__(self) -> str: return "Text"


@dataclass(frozen=True)
class TList(Type):
    elem: Type
    def __str__(self) -> str: return f"List[{self.elem}]"


@dataclass(frozen=True)
class TOption(Type):
    elem: Type
    def __str__(self) -> str: return f"Option[{self.elem}]"


@dataclass(frozen=True)
class TAny(Type):
    """Tipo aún desconocido: el de `[]` o `None` antes de unificar."""
    def __str__(self) -> str: return "?"


INT, BOOL, TEXT, ANY = TInt(), TBool(), TText(), TAny()


def unify(a: Type, b: Type) -> Type | None:
    """Devuelve el tipo común o None si son incompatibles."""
    if isinstance(a, TAny):
        return b
    if isinstance(b, TAny):
        return a
    if type(a) is not type(b):
        return None
    if isinstance(a, (TList, TOption)):
        e = unify(a.elem, b.elem)  # type: ignore[attr-defined]
        return None if e is None else type(a)(e)
    return a


# ---------- expresiones ----------

@dataclass
class Expr:
    line: int = field(default=0, kw_only=True)
    col: int = field(default=0, kw_only=True)


@dataclass
class IntLit(Expr):
    value: int


@dataclass
class BoolLit(Expr):
    value: bool


@dataclass
class TextLit(Expr):
    value: str


@dataclass
class NoneLit(Expr):
    pass


@dataclass
class SomeExpr(Expr):
    inner: Expr


@dataclass
class ListLit(Expr):
    items: list[Expr]


@dataclass
class Name(Expr):
    id: str


@dataclass
class Call(Expr):
    name: str
    args: list[Expr]


@dataclass
class Unary(Expr):
    op: str  # '-' | 'not'
    operand: Expr


@dataclass
class Binary(Expr):
    op: str
    left: Expr
    right: Expr


@dataclass
class If(Expr):
    cond: Expr
    then: Expr
    otherwise: Expr


# ---------- patrones ----------

@dataclass
class Pattern:
    line: int = field(default=0, kw_only=True)
    col: int = field(default=0, kw_only=True)


@dataclass
class PEmpty(Pattern):
    pass


@dataclass
class PCons(Pattern):
    head: str
    tail: str


@dataclass
class PNone(Pattern):
    pass


@dataclass
class PSome(Pattern):
    name: str


@dataclass
class PWild(Pattern):
    name: str | None  # None para `_`


@dataclass
class Arm:
    pattern: Pattern
    body: Expr


@dataclass
class Match(Expr):
    subject: Expr
    arms: list[Arm]


# ---------- funciones ----------

@dataclass
class Param:
    name: str
    type: Type


@dataclass
class Fn:
    name: str
    params: list[Param]
    ret: Type
    requires: list[Expr]
    ensures: list[Expr]
    effects: str | None
    examples: list[Expr]
    body: Expr
    line: int = 0
    col: int = 0


@dataclass
class Program:
    fns: list[Fn]
