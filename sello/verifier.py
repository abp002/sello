"""La huella del verificador: con qué se dio un certificado (SEL-7).

Un nivel 2 dice que Z3 no encontró contraejemplo a lo que el traductor le pasó, y un nivel 1
que el intérprete dio lo que decían los ejemplos. Valen lo que valgan el código de Sello que
decide y la versión de Z3: si cambian, el certificado no se reutiliza (`same`). La máquina
se apunta pero no invalida: con otro procesador Z3 encuentra o no encuentra la prueba
(SEL-4), pero lo que probó sigue probado. El reloj tampoco entra: solo corta, y un corte
deja nivel 1, que se reintenta siempre.
"""

from __future__ import annotations

import ast
import functools
import hashlib
import platform
from pathlib import Path

import z3

# Lo que decide un certificado. Fuera: el almacén, la CLI, el MCP, el hash (cambiarlo cambia
# los hashes, no los veredictos), el reimpresor y los mensajes de error.
MODULES = ("lexer", "parser", "nodes", "builtins", "checker", "interp", "compile", "prover")


def _sin_docstrings(tree: ast.AST) -> ast.AST:
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                node.body = body[1:] or [ast.Pass()]
    return tree


def code_hash(sources: list[str]) -> str:
    """Hash de los fuentes sin comentarios ni docstrings: documentar no invalida certificados.
    Se hashea `ast.unparse`, que cambia menos que `ast.dump` entre versiones de Python."""
    h = hashlib.sha256()
    for src in sources:
        h.update(ast.unparse(_sin_docstrings(ast.parse(src))).encode())
        h.update(b"\0")
    return h.hexdigest()[:16]


@functools.cache
def fingerprint() -> dict:
    here = Path(__file__).parent
    return {"sello": code_hash([(here / f"{m}.py").read_text() for m in MODULES]),
            "z3": z3.get_version_string(), "arch": platform.machine()}


def same(a: dict | None, b: dict) -> bool:
    """Si un certificado dado con `a` vale con `b`."""
    return a is not None and a.get("sello") == b["sello"] and a.get("z3") == b["z3"]
