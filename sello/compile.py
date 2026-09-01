"""El pipeline: texto -> AST -> comprobación -> ejemplos ejecutados -> resumen."""

from __future__ import annotations

from .checker import Checker, signature
from .errors import SelloError
from .interp import Interpreter, fmt
from .nodes import Binary, Program
from .parser import parse
from .pretty import unparse


def compile_source(src: str) -> tuple[Program, Interpreter]:
    """Parsea y comprueba estáticamente. No ejecuta ejemplos."""
    program = parse(src)
    Checker(program).check()
    return program, Interpreter(program)


def run_examples(program: Program, interp: Interpreter) -> int:
    """Ejecuta todos los `example`. Devuelve cuántos pasaron; lanza E200 en el primero que falle."""
    count = 0
    for fn in program.fns:
        for ex in fn.examples:
            if isinstance(ex, Binary) and ex.op == "==":
                got = interp.eval(ex.left, {}, fn.name)
                expected = interp.eval(ex.right, {}, fn.name)
                if got != expected:
                    raise SelloError(
                        "E200",
                        f"`{unparse(ex.left)}` expected {fmt(expected)}, got {fmt(got)}",
                        ex.line, ex.col, fn.name,
                        {"expected": fmt(expected), "got": fmt(got)},
                    )
            elif not interp.eval(ex, {}, fn.name):
                raise SelloError("E200", f"`{unparse(ex)}` evaluated to false", ex.line, ex.col, fn.name)
            count += 1
    return count


def check_source(src: str) -> dict:
    """Todo el pipeline. Devuelve el resumen que imprime `sello check`."""
    program, interp = compile_source(src)
    n = run_examples(program, interp)
    return {
        "ok": True,
        "functions": [
            {"name": fn.name, "signature": signature(fn), "examples": len(fn.examples)}
            for fn in program.fns
        ],
        "examples": n,
    }
