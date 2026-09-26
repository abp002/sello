#!/usr/bin/env python3
"""Z3 no cierra con `seq.nth` una deducción de dos pasos que con arrays es inmediata (ALE-193).

Es el núcleo de por qué `dedupe` de ejemplos/basicos.sello no llega a nivel 2: para
`distinct([h] ++ r)`, el caso del primer elemento es `hr[0] == hr[b]` con `b >= 1`, y basta con
`hr[b] == r[b - 1]` (hecho de concatenación) y `r[b - 1] != h` (`h` no está en `r`). Los mismos
hechos, con las listas como `Seq Int` de Z3 o como arrays con la longitud aparte:

    uv run python bench/seq_nth.py

Medido el 2026-09-26: con secuencias, timeout en Z3 4.12.6, 4.13.4, 4.14.1, 4.15.3 y 5.1.0; con
arrays, unsat en 0,00 s. No es una regresión: la teoría de secuencias intenta construir la
secuencia, y con longitud simbólica no termina.
"""

from __future__ import annotations

import time

import z3


def caso(listas: str, ms: int = 10_000) -> tuple[z3.CheckSatResult, float]:
    s = z3.Solver()
    s.set("timeout", ms)
    h, b, i, q = z3.Ints("h b i q")
    if listas == "arrays":
        hr, r = z3.Array("hr", z3.IntSort(), z3.IntSort()), z3.Array("r", z3.IntSort(), z3.IntSort())
        len_hr, len_r = z3.Ints("len_hr len_r")
        s.add(len_r >= 0)
    else:
        seq = z3.SeqSort(z3.IntSort())
        hr, r = z3.Const("hr", seq), z3.Const("r", seq)
        len_hr, len_r = z3.Length(hr), z3.Length(r)
    s.add(len_hr == 1 + len_r, hr[0] == h)                                       # hr = [h] ++ r
    s.add(z3.ForAll([i], z3.Implies(z3.And(i >= 1, i < len_hr), hr[i] == r[i - 1]), patterns=[hr[i]]))
    s.add(z3.ForAll([q], z3.Implies(z3.And(q >= 0, q < len_r), r[q] != h), patterns=[r[q]]))  # h no está en r
    s.add(b >= 1, b < len_hr, hr[0] == hr[b])                                    # negación del objetivo
    t0 = time.monotonic()
    return s.check(), time.monotonic() - t0


if __name__ == "__main__":
    print(z3.get_full_version())
    for listas in ("secuencias", "arrays"):
        r, t = caso(listas)
        print(f"{listas:10s} {r} {t:.2f} s")
