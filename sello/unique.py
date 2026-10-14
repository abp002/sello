"""¿El contrato fija una sola respuesta? (SEL-8)

Z3 busca una entrada que cumpla `requires` y dos resultados distintos que cumplan el `ensures`.
Solo mira el contrato: el cuerpo no entra, y un hueco (`sorry`) se comprueba igual.

  unique     no hay dos: para cada entrada que cumpla `requires`, todos los cuerpos que cumplan
             el contrato devuelven lo mismo (si las funciones llamadas cumplen el suyo)
  ambiguous  hay dos, y el intérprete evaluó el contrato con la entrada y los dos resultados y
             los dos lo cumplen: el testigo
  unknown    Z3 no decidió, o sus candidatos no se confirmaron al ejecutarlos

Las llamadas dentro del contrato se modelan por su contrato, como en el nivel 2: un `unique` vale
para cualquier cuerpo de lo llamado que cumpla su contrato. Un candidato puede salir de ahí (dos
resultados que solo valen si lo llamado devolviera otra cosa de la que devuelve), y por eso todo
testigo se ejecuta antes de afirmarlo, como los contraejemplos del probador. El contrato propio
no es axioma (DD0435): si no tiene resultado para alguna entrada, no puede volver inconsistentes
las hipótesis.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass

import z3

from .checker import Checker
from .errors import SelloError
from .interp import Interpreter, fmt
from .nodes import BOOL, Fn, Program, TList
from .parser import parse
from .prover import (
    CONFIRM_FUEL, PHASES, RETRIES, Budget, Env, Stuck, Translator, Unsupported, query, too_big,
    value,
)

UNIQUE, AMBIGUOUS, UNKNOWN = "unique", "ambiguous", "unknown"


@dataclass
class Uniqueness:
    status: str
    reason: str = ""             # para unknown
    witness: dict | None = None  # para ambiguous: args, results, input
    ms: int = 0


def _holds(interp: Interpreter, fn: Fn, args: list, result: object) -> bool:
    """¿Cumplen esa entrada y ese resultado el contrato, ejecutándolo? Un error al evaluarlo
    (requires de lo llamado, índice fuera, combustible) es que no."""
    env = {p.name: a for p, a in zip(fn.params, args)}
    interp.fuel = CONFIRM_FUEL
    try:
        return (all(interp.eval(r, env, fn.name) is True for r in fn.requires)
                and all(interp.eval(c, {**env, "result": result}, fn.name) is True for c in fn.ensures))
    except (SelloError, RecursionError):
        return False
    finally:
        interp.fuel = None


def _other(tr: Translator, fn: Fn, params: list, results: list, args: list, rs: list) -> z3.BoolRef:
    """Fuera ese trío: otra entrada, u otros dos resultados para la misma."""
    return z3.Or([*[c != tr.term(a, p.type) for c, a, p in zip(params, args, fn.params)],
                  *[x != tr.term(v, fn.ret) for x, v in zip(results, rs)]])


def unique(program: Program, fn: Fn, interp: Interpreter | None = None,
           budget: Budget | None = None) -> Uniqueness:
    t0 = time.monotonic()
    budget = budget or Budget()
    budget.start_fn()
    interp = interp or Interpreter(program)

    def done(status: str, reason: str = "", witness: dict | None = None) -> Uniqueness:
        return Uniqueness(status, reason, witness, int((time.monotonic() - t0) * 1000))

    ctx = z3.Context()
    try:
        tr = Translator(program, fn, ctx)
        params = [z3.Const(p.name, tr.sort(p.type)) for p in fn.params]
        env = Env({p.name: c for p, c in zip(fn.params, params)}, {p.name: p.type for p in fn.params})
        req: list = []
        for r in fn.requires:
            req.append(tr.expr(r, env, req, BOOL))
        results = [z3.Const(f"result!{k}", tr.sort(fn.ret)) for k in (1, 2)]
        ens: list = []
        for res in results:
            renv = env.bind("result", res, fn.ret)
            prev: list = []
            for c in fn.ensures:
                prev.append(tr.expr(c, renv, prev, BOOL))
            ens += prev
        # Los axiomas de lo que aparece, por hash, como en `_setup`; el propio contrato no.
        seen: set[str] = {fn.name}
        base: list = []
        while set(tr.ufs) - seen:
            name = min(set(tr.ufs) - seen, key=lambda n: (tr.canon[n], n))
            seen.add(name)
            try:
                base.append(tr.axiom(tr.fns[name]))
            except Unsupported:
                continue
        r1, r2 = results
        differ = [r1 != r2]
        if isinstance(fn.ret, TList):
            # `xs[i]` es `at`, no interpretada: dos listas con la misma longitud y los mismos `at`
            # pueden ser dos términos distintos para Z3. Que difieran es que lo diga una posición.
            k = z3.Int("k!differ", ctx)
            differ.append(z3.Or(z3.Length(r1) != z3.Length(r2),
                                z3.And(k >= 0, k < z3.Length(r1), tr.at(r1, k) != tr.at(r2, k))))
        core = [*base, *req, *ens, *differ]
        # Primero sin los axiomas de `at` y `cat!`: con ellos, la teoría de secuencias parte cada
        # lista en unidades y el patrón de `unit` no acaba (una lista ordenada de longitud 1 ya
        # agotaba el trabajo). Quitar hipótesis verdaderas no cambia lo que vale un unsat, y todo
        # testigo se ejecuta. Con ellos después, para lo que solo se prueba sabiendo qué es `at`.
        # Sin ellos `at` queda libre y el modelo no casa con la lista que da (un `contains` en el
        # requires salía falso al ejecutarlo). Para las listas de la consulta, y solo para ellas,
        # `at` es `seq.nth` dentro del rango: verdadero, y no se dispara sobre cada trozo de lista
        # que cree la teoría (con `forall` sobre toda secuencia volvía el bucle).
        nth = []
        for v in [*params, *results]:
            if isinstance(v.sort(), z3.SeqSortRef) and not v.sort().is_string():
                i = z3.Int(f"i[{v}]!nth", ctx)
                at = tr.at_fn(v.sort().basis())
                nth.append(z3.ForAll([i], z3.Implies(z3.And(i >= 0, i < z3.Length(v)), at(v, i) == v[i]),
                                     patterns=[at(v, i)]))
        solvers = []
        for facts in (nth, tr.facts):
            s = z3.Solver(ctx=ctx)
            s.add(*core, *facts)
            solvers.append(s)
    except Unsupported as u:
        return done(UNKNOWN, f"unsupported: {u}")
    except z3.Z3Exception as z:
        return done(UNKNOWN, f"z3: {str(z).strip()[:120]}")

    tried = 0
    excluded: list = []  # tríos ya ejecutados sin confirmar, en valores del intérprete
    reason = "undecided"
    try:
        for s in solvers:
            for args, rs in excluded:
                s.add(_other(tr, fn, params, results, args, rs))
            for _, mbqi, cap in [ph for ph in PHASES if ph[0] == "s"]:
                while True:
                    got = query(s, ctx, budget, mbqi, cap)
                    if got is None:
                        return done(UNKNOWN, "timeout")
                    r, model = got
                    if r == z3.unsat:
                        # Con candidatos descartados, unsat no prueba nada: se descartaron ejecutando.
                        return done(UNIQUE) if not excluded else done(UNKNOWN, reason)
                    if model is None:
                        break  # unknown sin candidato: la fase siguiente
                    try:
                        args = [value(model.eval(c, model_completion=True), p.type) for p, c in zip(fn.params, params)]
                        rs = [value(model.eval(x, model_completion=True), fn.ret) for x in results]
                    except (Unsupported, z3.Z3Exception):
                        reason = "candidate not concrete"
                        break
                    if rs[0] != rs[1] and not any(too_big(v) for v in [*args, *rs]) \
                            and all(_holds(interp, fn, args, x) for x in rs):
                        shown = f"{fn.name}(" + ", ".join(fmt(a) for a in args) + ")"
                        return done(AMBIGUOUS, witness={"args": args, "results": rs, "input": shown})
                    excluded.append((args, rs))
                    reason = "candidates did not hold when executed"
                    if len(excluded) > RETRIES:
                        return done(UNKNOWN, reason)
                    s.add(_other(tr, fn, params, results, args, rs))
    except Stuck as st:
        return done(UNKNOWN, str(st))
    except z3.Z3Exception as z:
        return done(UNKNOWN, f"z3: {str(z).strip()[:120]}")
    return done(UNKNOWN, reason)


def _main(argv: list[str]) -> int:
    """Proceso hijo para bench: programa por stdin, una línea JSON por función de `--only` (o
    todas). Z3 puede colgarse o morir; quien lo lanza pone el reloj."""
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    a = ap.parse_args(argv)
    only = None if a.only is None else set(filter(None, a.only.split(",")))
    try:
        program = parse(sys.stdin.read())
        Checker(program).check()
    except SelloError as e:
        print(json.dumps({"fatal": f"{e.code} {e.detail}"}), flush=True)
        return 1
    interp = Interpreter(program)
    budget = Budget()
    for fn in program.fns:
        if only is not None and fn.name not in only:
            continue
        u = unique(program, fn, interp, budget)
        w = None if u.witness is None else {
            "input": u.witness["input"], "results": [fmt(x) for x in u.witness["results"]]}
        print(json.dumps({"name": fn.name, "status": u.status, "reason": u.reason, "ms": u.ms,
                          "witness": w}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
