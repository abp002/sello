"""Vocabulario de contratos: funciones sobre listas válidas solo en `requires` y
`ensures`. Los nombres están reservados. Decisión: 'Los contratos tienen vocabulario
propio para listas' (vault, 2026-09-02).
"""

from __future__ import annotations

# nombre -> aridad
NAMES: dict[str, int] = {"len": 1, "count": 2, "contains": 2, "distinct": 1, "sorted": 1}

QUANTIFIERS = ("forall", "exists")


def run(name: str, args: list) -> object:
    xs = args[0]
    if name == "len":
        return len(xs)
    if name == "count":
        return sum(1 for x in xs if x == args[1])
    if name == "contains":
        return any(x == args[1] for x in xs)
    if name == "distinct":
        return all(xs[i] != xs[j] for i in range(len(xs)) for j in range(i + 1, len(xs)))
    if name == "sorted":
        return all(a <= b for a, b in zip(xs, xs[1:]))
    raise KeyError(name)
