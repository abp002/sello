#!/usr/bin/env python3
"""Qué cuantificadores instancia Z3, y con qué patrones, al probar una función (ALE-249).

Para diagnosticar una prueba que se queda sin trabajo. Cada cuantificador que crea el probador
lleva como `qid` el método y la línea de `sello/prover.py` que lo crea (`facts_concat:724`).

  instancias (por defecto)  `smt.qi.profile` de Z3 sumado por qid: cuántas instancias en todas
                            las consultas de la función (fases exactas y u) y la generación máxima
  --obligacion k            los patrones con los que trabaja Z3 de verdad, también los que infiere
                            él cuando el probador no los da. Salen del log de traza de Z3
                            (`trace=true`), con la obligación k montada como en el probador y poco
                            trabajo (`--trabajo`)

    uv run python bench/patrones.py programa.sello SplitAndAppend
    uv run python bench/patrones.py programa.sello SplitAndAppend --obligacion 6

Medido el 2026-09-28 con DD0753 (ALE-249): el axioma global `at(a ++ b, i)` se instancia más de
5.000 veces porque casa con las concatenaciones que crea la teoría de secuencias al descomponer
cada lista (`l = unit(nth_i(l, 0)) ++ tail(l, 0)`), y el contrato de `take` tiene dos
patrones inferidos, uno del lado de la entrada (`at(xs, i)`).
"""

from __future__ import annotations

import argparse
import collections
import gc
import inspect
import os
import re
import sys
import tempfile
from pathlib import Path

import z3

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sello import prover as P  # noqa: E402
from sello.checker import Checker  # noqa: E402
from sello.parser import parse  # noqa: E402


def _con_qid(original):
    def cuantificador(vs, body, *a, **kw):
        llamador = inspect.stack()[1]
        if not kw.get("qid") and llamador.filename.endswith("prover.py"):
            kw["qid"] = f"{llamador.function}:{llamador.lineno}"
        return original(vs, body, *a, **kw)
    return cuantificador


z3.ForAll, z3.Exists = _con_qid(z3.ForAll), _con_qid(z3.Exists)


def instancias(program, fn) -> None:
    """Z3 escribe el perfil por stderr al destruir cada contexto: se recoge del descriptor 2."""
    z3.set_param("smt.qi.profile", True)
    with tempfile.TemporaryFile(mode="w+") as tmp:
        sys.stderr.flush()
        fd = os.dup(2)
        os.dup2(tmp.fileno(), 2)
        try:
            v = P.prove(program, fn)
            gc.collect()
        finally:
            os.dup2(fd, 2)
            os.close(fd)
        tmp.seek(0)
        perfil = tmp.read()
    total: collections.Counter = collections.Counter()
    gen: dict[str, int] = {}
    for linea in perfil.splitlines():
        m = re.match(r"\[quantifier_instances\]\s+(\S+)\s*:\s*(\d+)\s*:\s*\d+\s*:\s*\d+\s*:\s*(\d+)", linea)
        if m:
            total[m.group(1)] += int(m.group(2))
            gen[m.group(1)] = max(gen.get(m.group(1), 0), int(m.group(3)))
    print(f"{fn.name}: {v.status} {v.reason} ({v.ms} ms)\n")
    print(f"{'qid':24s} {'instancias':>10s} {'gen. máx':>9s}")
    for qid, n in total.most_common():
        print(f"{qid:24s} {n:10d} {gen[qid]:9d}")


def patrones(program, fn, k: int, trabajo: int) -> None:
    with tempfile.TemporaryDirectory() as d:
        log = Path(d, "z3.log")
        z3.set_param("trace", True)
        z3.set_param("trace_file_name", str(log))
        ctx = z3.Context()
        tr = P.Translator(program, fn, ctx)
        params = [z3.Const(p.name, tr.sort(p.type)) for p in fn.params]
        env = P.Env({p.name: c for p, c in zip(fn.params, params)}, {p.name: p.type for p in fn.params})
        s = P._setup(tr, fn, env)
        o = tr.obligations[k]
        s.add(*o.path)
        s.add(z3.Not(o.prop))
        s.set("rlimit", trabajo)
        s.set("smt.mbqi", False)
        r = s.check()
        print(f"obligación {k} ({o.code} {o.what}): {r} {s.reason_unknown() if r == z3.unknown else ''}\n")
        del s, tr, ctx
        gc.collect()
        z3.set_param("trace", False)
        terminos: dict[str, tuple] = {}

        def ver(t: str, hondo: int = 0) -> str:
            x = terminos.get(t)
            if x is None:
                return t
            clase, nombre, args = x
            if clase == "var":
                return f"?{nombre}"
            if not args:
                return nombre
            if hondo > 5:
                return nombre + "(…)"
            return f"{nombre}(" + ", ".join(ver(a, hondo + 1) for a in args) + ")"

        vistos = set()
        for linea in log.read_text(errors="replace").splitlines():
            m = re.match(r"\[mk-app\] (#\d+) (\S+)(.*)", linea)
            if m:
                terminos[m.group(1)] = ("app", m.group(2), re.findall(r"#\d+", m.group(3)))
                continue
            m = re.match(r"\[mk-var\] (#\d+) (\d+)", linea)
            if m:
                terminos[m.group(1)] = ("var", m.group(2), [])
                continue
            m = re.match(r"\[mk-quant\] #\d+ (\S+) \d+(.*)", linea)
            if m and ":" in m.group(1):  # los nuestros; Z3 declara los suyos (k!N)
                ids = re.findall(r"#\d+", m.group(2))[:-1]  # el último es el cuerpo
                pats = " | ".join(ver(p).removeprefix("pattern(").removesuffix(")") for p in ids)
                if pats and (m.group(1), pats) not in vistos:
                    vistos.add((m.group(1), pats))
                    print(f"{m.group(1).strip('|'):24s} {pats}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("programa", type=Path)
    ap.add_argument("funcion")
    ap.add_argument("--obligacion", type=int, default=None)
    ap.add_argument("--trabajo", type=int, default=20_000)
    a = ap.parse_args()
    program = parse(a.programa.read_text())
    Checker(program).check()
    fn = next(f for f in program.fns if f.name == a.funcion)
    if a.obligacion is None:
        instancias(program, fn)
    else:
        patrones(program, fn, a.obligacion, a.trabajo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
