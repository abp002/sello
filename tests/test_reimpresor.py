"""Propiedad del reimpresor: reparsear el texto canónico devuelve el mismo AST.

Los dos bugs del 2026-09-05 (`if`/`match` y `forall` como operando perdían los paréntesis)
eran fallos de esta propiedad en casos que nadie había escrito a mano. El almacén guarda el
texto reimpreso y hashea el AST original, así que esta propiedad es lo que hace que el
certificado acredite la función que dice acreditar.
"""

from dataclasses import fields, is_dataclass

from hypothesis import given, settings
from hypothesis import strategies as st

from sello.lexer import KEYWORDS
from sello.nodes import (
    Arm, Binary, BoolLit, Call, If, IntLit, ListLit, Match, Name, NoneLit,
    PCons, PEmpty, PNone, PSome, PWild, Quant, SomeExpr, TextLit, Unary,
)
from sello.parser import parse_expr
from sello.pretty import unparse

nombre = st.from_regex(r"[a-zA-Z][a-zA-Z0-9_]{0,4}", fullmatch=True).filter(lambda s: s not in KEYWORDS)
nombre_o_guion = st.one_of(st.just("_"), nombre)
texto = st.text(min_size=0, max_size=6)

hoja = st.one_of(
    st.integers(min_value=0, max_value=10**6).map(IntLit),  # `-3` es Unary("-", IntLit(3))
    st.booleans().map(BoolLit),
    texto.map(TextLit),
    st.just(NoneLit()),
    nombre.map(Name),
)

OPS = ["+", "-", "*", "/", "%", "==", "!=", "<", "<=", ">", ">=", "and", "or", "++"]

patron = st.one_of(
    st.just(PEmpty()),
    st.builds(PCons, nombre_o_guion, nombre_o_guion),
    st.just(PNone()),
    st.builds(PSome, nombre),
    st.builds(PWild, st.one_of(st.none(), nombre)),
)


# `st.deferred` en vez de `st.recursive`: mismo árbol, sin el repr de megabytes que hypothesis
# construye para las estrategias anidadas. Las hojas van repetidas para que los árboles acaben.
expresion = st.deferred(lambda: st.one_of(
    hoja, hoja,
    st.builds(SomeExpr, expresion),
    st.lists(expresion, max_size=3).map(ListLit),
    st.builds(Call, nombre, st.lists(expresion, max_size=3)),
    st.builds(Unary, st.sampled_from(["-", "not"]), expresion),
    st.builds(Binary, st.sampled_from(OPS), expresion, expresion),
    st.builds(If, expresion, expresion, expresion),
    st.builds(Match, expresion, st.lists(st.builds(Arm, patron, expresion), min_size=1, max_size=3)),
    st.builds(Quant, st.sampled_from(["forall", "exists"]), nombre, expresion, expresion),
))


def forma(x):
    """El AST sin posiciones: lo que el hash mira y lo que el reimpresor debe conservar."""
    if is_dataclass(x):
        return (type(x).__name__, *(forma(getattr(x, f.name)) for f in fields(x) if f.name not in ("line", "col")))
    if isinstance(x, list):
        return tuple(forma(i) for i in x)
    return x


@settings(max_examples=500)
@given(expresion)
def test_reparsear_el_texto_canonico_da_el_mismo_ast(e):
    txt = unparse(e)
    assert forma(parse_expr(txt)) == forma(e), txt
