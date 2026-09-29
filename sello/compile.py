"""El pipeline: texto -> AST -> comprobación -> ejemplos ejecutados -> probador -> resumen."""

from __future__ import annotations

from .checker import Checker, signature
from .errors import SelloError
from .interp import Interpreter, fmt
from .nodes import Binary, Expr, Fn, Program
from .parser import parse
from .pretty import unparse
from .prover import PROVEN, Verdict, first_error, prove_program


def compile_source(src: str) -> tuple[Program, Interpreter]:
    """Parsea y comprueba estáticamente. No ejecuta ejemplos."""
    program = parse(src)
    Checker(program).check()
    return program, Interpreter(program)


def run_examples(program: Program, interp: Interpreter,
                 pending: list[tuple[str, str]] | None = None) -> int:
    """Ejecuta todos los `example`. Devuelve cuántos pasaron; lanza E200 en el primero que falle.
    Un ejemplo que llega a un hueco (`{ sorry }`, E502) ni pasa ni falla: con `pending` se apunta
    ahí, como (función, ejemplo), y se sigue; sin él, el E502 se lanza."""
    count = 0
    for fn in program.fns:
        for ex in fn.examples:
            try:
                _run_example(fn.name, ex, interp)
            except SelloError as e:
                if e.code == "E502" and pending is not None:
                    pending.append((fn.name, unparse(ex)))
                    continue
                raise
            count += 1
    return count


def _run_example(name: str, ex: Expr, interp: Interpreter) -> None:
    if isinstance(ex, Binary) and ex.op == "==":
        got = interp.eval(ex.left, {}, name)
        expected = interp.eval(ex.right, {}, name)
        if got != expected:
            raise SelloError(
                "E200",
                f"`{unparse(ex.left)}` expected {fmt(expected)}, got {fmt(got)}",
                ex.line, ex.col, name,
                {"expected": fmt(expected), "got": fmt(got)},
            )
    elif not interp.eval(ex, {}, name):
        raise SelloError("E200", f"`{unparse(ex)}` evaluated to false", ex.line, ex.col, name)


def level(proven: bool, pending: int, hole: bool = False) -> int:
    """El nivel de un certificado. 2: el contrato está probado para toda entrada, dado lo que
    prometen los contratos de lo que se llama; 1: los ejemplos pasaron, todos; 0: nada establecido
    todavía, porque la función es un hueco o porque algún ejemplo espera a uno."""
    if hole:
        return 0
    if proven:
        return 2
    return 0 if pending else 1


def prove(program: Program, only: set[str] | None = None) -> dict[str, Verdict]:
    """Nivel 2 sobre el programa (o solo sobre `only`). Un contraejemplo real (ya ejecutado) se lanza."""
    verdicts = prove_program(program, only=only)
    e = first_error(verdicts)
    if e is not None:
        raise e
    return verdicts


def check_source(src: str, prover: bool = True, store=None) -> dict:
    """Todo el pipeline. Devuelve el resumen que imprime `sello check`. Con `store`, lo que el
    fuente llama y no define se enlaza desde el almacén (`Store.link`); el resumen habla solo
    de las funciones del fuente."""
    program = parse(src)
    names = {f.name for f in program.fns}
    if store is not None:
        program, _ = store.link(program)
    Checker(program).check()
    interp = Interpreter(program)
    own = [fn for fn in program.fns if fn.name in names]
    pending: list[tuple[str, str]] = []
    n = run_examples(Program(own), interp, pending)
    verdicts = prove(program, only={fn.name for fn in own if not fn.hole}) if prover else {}
    out: dict = {
        "ok": True,
        "functions": [_summary(fn, verdicts, sum(1 for f, _ in pending if f == fn.name), prover)
                      for fn in own],
        "examples": n,
    }
    if prover:
        out["proven"] = sum(1 for v in verdicts.values() if v.status == PROVEN)
    return out


def _summary(fn: Fn, verdicts: dict[str, Verdict], pending: int, prover: bool) -> dict:
    d: dict = {"name": fn.name, "signature": signature(fn), "examples": len(fn.examples)}
    if fn.name in verdicts:
        d.update(verdicts[fn.name].to_dict())
    if prover:
        d["level"] = level(verdicts[fn.name].status == PROVEN if fn.name in verdicts else False,
                           pending, fn.hole)
    if fn.hole:
        d["hole"] = True
    if pending:
        d["pending"] = pending
    return d
