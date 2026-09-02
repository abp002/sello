"""Errores de Sello: datos estructurados para agentes, no texto para personas.

Cada error tiene un código estable, una posición, qué pasó, cómo se arregla y un
ejemplo de código correcto. Se serializa a JSON. La tabla de códigos vive en spec/SPEC.md
y ESTE fichero es la fuente de verdad de los textos.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

_EJEMPLO_FN = (
    "fn factorial(n: Int) -> Int\n"
    "  requires n >= 0\n"
    "  ensures result >= 1\n"
    "  effects pure\n"
    "  example factorial(5) == 120\n"
    "{\n"
    "  if n == 0 then 1 else n * factorial(n - 1)\n"
    "}"
)

# code -> (what, fix, example)
CATALOGO: dict[str, tuple[str, str, str]] = {
    "E000": (
        "Syntax error",
        "Follow the grammar in the spec. One function per `fn`, clauses before the body, body in braces.",
        _EJEMPLO_FN,
    ),
    "E100": (
        "Missing contract clause",
        "Every function needs `requires`, `ensures`, `effects` and at least one `example`.",
        _EJEMPLO_FN,
    ),
    "E101": (
        "Unknown effect",
        "In v0 the only effect is `pure`. Write `effects pure`.",
        "  effects pure",
    ),
    "E102": (
        "Trivial contract clause",
        "`requires true` and `ensures true` certify nothing. State what the task lets you assume about the arguments, and a property that a wrong result would break.",
        "  requires n >= 0\n  ensures result >= 1",
    ),
    "E200": (
        "Example failed",
        "The body or the example is wrong. Compare expected and got, then fix one of them.",
        "  example max(1, 2) == 2",
    ),
    "E201": (
        "Postcondition violated",
        "The body returned a value that does not satisfy `ensures`. Fix the body, or weaken `ensures` if it is wrong.",
        "  ensures result >= a and result >= b",
    ),
    "E300": (
        "Precondition violated at call",
        "The caller passed arguments that do not satisfy the callee's `requires`. Guard the call with `if`, or strengthen the caller's own `requires`.",
        "  if n == 0 then 1 else n * factorial(n - 1)",
    ),
    "E400": (
        "Type mismatch",
        "Make both sides the same type. Arithmetic needs Int, conditions need Bool, list elements must share a type.",
        "  if xs == [] then 0 else 1",
    ),
    "E401": (
        "Unknown name",
        "Use a parameter, a function defined in this file, or `result` inside `ensures`. `len`, `count`, `contains`, `distinct`, `sorted`, `forall` and `exists` exist only inside `requires` and `ensures`.",
        "fn f(x: Int) -> Int ... { x + 1 }",
    ),
    "E402": (
        "Duplicate definition",
        "Each function name is defined once per file. `len`, `count`, `contains`, `distinct` and `sorted` are reserved. Rename or remove one.",
        "",
    ),
    "E403": (
        "Wrong number of arguments",
        "Pass exactly as many arguments as parameters in the signature.",
        "  max(1, 2)",
    ),
    "E404": (
        "Non-exhaustive match",
        "Cover every case: `[]` and `[h, ..t]` for List, `None` and `Some(x)` for Option, or add `_ =>`.",
        "match xs {\n  [] => 0\n  [h, ..t] => h + sum(t)\n}",
    ),
    "E500": (
        "Runtime error",
        "The message says what happened (division by zero, recursion too deep). Add a `requires` that rules the input out.",
        "  requires b != 0",
    ),
}


@dataclass
class SelloError(Exception):
    code: str
    detail: str = ""
    line: int = 0
    col: int = 0
    function: str | None = None
    extra: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.code not in CATALOGO:
            raise ValueError(f"código de error desconocido: {self.code}")
        super().__init__(self.detail or CATALOGO[self.code][0])

    def to_dict(self) -> dict:
        what, fix, example = CATALOGO[self.code]
        where: dict = {"line": self.line, "col": self.col}
        if self.function:
            where["function"] = self.function
        d: dict = {
            "code": self.code,
            "where": where,
            "what": f"{what}: {self.detail}" if self.detail else what,
            "fix": fix,
        }
        if example:
            d["example"] = example
        d.update(self.extra)
        return d

    def to_json(self) -> str:
        return json.dumps({"ok": False, "error": self.to_dict()}, ensure_ascii=False, indent=2)
