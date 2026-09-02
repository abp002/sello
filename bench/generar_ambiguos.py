#!/usr/bin/env python3
"""Genera la batería del juez imperfecto: `bench/ambiguos/*.json`.

Cada problema tiene un enunciado con un dominio obligatorio declarado y una zona ambigua
(lo que el enunciado calla). Los casos del oráculo los calcula una implementación de
referencia en Python, con semilla fija. La política de referencia en la zona ambigua es
arbitraria y está escrita aquí; la suerte de acertarla es simétrica entre lenguajes.

    uv run python bench/generar_ambiguos.py

Se ejecuta una vez y el resultado se commitea antes de la primera corrida.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

SALIDA = Path(__file__).resolve().parent / "ambiguos"
SEMILLA = 20260902
N_DOMINIO = 25


def lista(rng: random.Random, n: int | None = None, lo: int = -9, hi: int = 9) -> list[int]:
    if n is None:
        n = rng.randint(0, 7)
    return [rng.randint(lo, hi) for _ in range(n)]


def distintos(rng: random.Random, n: int | None = None) -> list[int]:
    if n is None:
        n = rng.randint(0, 7)
    return rng.sample(range(-20, 21), n)


# ---------- referencias ----------

def ref_clamp(x, lo, hi):
    return max(lo, min(x, hi))


def ref_index_of(xs, x):
    return xs.index(x) if x in xs else -1


def ref_int_sqrt(n):
    if n < 0:
        return 0
    r = 0
    while (r + 1) * (r + 1) <= n:
        r += 1
    return r


def ref_longest_run(xs):
    best = cur = 0
    for i, v in enumerate(xs):
        cur = cur + 1 if i > 0 and xs[i - 1] == v else 1
        best = max(best, cur)
    return best


def ref_max_subarray(xs):
    if not xs:
        return 0
    best = cur = xs[0]
    for v in xs[1:]:
        cur = max(v, cur + v)
        best = max(best, cur)
    return best


def ref_merge_sorted(xs, ys):
    return sorted(xs + ys)


def ref_most_frequent(xs):
    if not xs:
        return None
    counts = {}
    for v in xs:
        counts[v] = counts.get(v, 0) + 1
    top = max(counts.values())
    return min(v for v, c in counts.items() if c == top)


def ref_nth(xs, i):
    return xs[i] if 0 <= i < len(xs) else None


def ref_power(base, exp):
    if exp < 0:
        return 0
    return base ** exp


def ref_rotate_left(xs, k):
    if not xs:
        return []
    k %= len(xs)
    return xs[k:] + xs[:k]


def ref_second_largest(xs):
    d = sorted(set(xs), reverse=True)
    return d[1] if len(d) >= 2 else None


def ref_zip_sum(xs, ys):
    return [a + b for a, b in zip(xs, ys)]


# ---------- problemas ----------
# statement: dominio obligatorio declarado. Lo que no dice es la zona ambigua.
# visible: dos casos de camino feliz que van en el enunciado (juez débil).
# ambiguous: inputs de la zona ambigua, a mano. dominio: generador aleatorio.

PROBLEMAS = [
    dict(
        fn="clamp", ref=ref_clamp, opt=False,
        sello="clamp(x: Int, lo: Int, hi: Int) -> Int",
        python="def clamp(x: int, lo: int, hi: int) -> int",
        statement="Limit x to the range from lo to hi: values below lo become lo, values above "
                  "hi become hi. Must work for any integers x, lo and hi with lo <= hi.",
        visible=[[5, 0, 10], [-3, 0, 10]],
        ambiguous=[[5, 10, 0], [0, 3, 1], [7, 7, 2], [-1, 2, -5]],
        dominio=lambda r: (lambda lo, hi: [r.randint(-15, 15), lo, hi])(*sorted([r.randint(-9, 9), r.randint(-9, 9)])),
    ),
    dict(
        fn="index_of", ref=ref_index_of, opt=False,
        sello="index_of(xs: List[Int], x: Int) -> Int",
        python="def index_of(xs: list[int], x: int) -> int",
        statement="Return the 0-based position of the first occurrence of x in xs. Must work for "
                  "any list that contains x at least once.",
        visible=[[[4, 7, 9], 7], [[3, 3, 3], 3]],
        ambiguous=[[[], 1], [[1, 2, 3], 4], [[5], 0]],
        dominio=lambda r: (lambda xs: [xs, r.choice(xs)])(lista(r, r.randint(1, 7))),
    ),
    dict(
        fn="int_sqrt", ref=ref_int_sqrt, opt=False,
        sello="int_sqrt(n: Int) -> Int",
        python="def int_sqrt(n: int) -> int",
        statement="Return the largest integer whose square does not exceed n. Must work for any "
                  "n >= 0.",
        visible=[[16], [17]],
        ambiguous=[[-1], [-4], [-100]],
        dominio=lambda r: [r.choice([0, 1, 2, 3, 4, 8, 9, 15, 24, 25, 99, 100, r.randint(0, 10000)])],
    ),
    dict(
        fn="longest_run", ref=ref_longest_run, opt=False,
        sello="longest_run(xs: List[Int]) -> Int",
        python="def longest_run(xs: list[int]) -> int",
        statement="Return the length of the longest run of equal consecutive elements. Must work "
                  "for any non-empty list.",
        visible=[[[1, 1, 2, 2, 2, 3]], [[7]]],
        ambiguous=[[[]]],
        dominio=lambda r: [lista(r, r.randint(1, 8), 1, 3)],
    ),
    dict(
        fn="max_subarray", ref=ref_max_subarray, opt=False,
        sello="max_subarray(xs: List[Int]) -> Int",
        python="def max_subarray(xs: list[int]) -> int",
        statement="Return the largest sum of a contiguous sublist. Must work for any list that "
                  "has at least one element greater than zero.",
        visible=[[[1, -2, 3, 4, -1]], [[2, 2, -5, 1]]],
        ambiguous=[[[]], [[-3, -1, -2]], [[-5]], [[0, -1, 0]]],
        dominio=lambda r: (lambda xs: [xs if any(v > 0 for v in xs) else xs + [r.randint(1, 9)]])(lista(r, r.randint(1, 7))),
    ),
    dict(
        fn="merge_sorted", ref=ref_merge_sorted, opt=False,
        sello="merge_sorted(xs: List[Int], ys: List[Int]) -> List[Int]",
        python="def merge_sorted(xs: list[int], ys: list[int]) -> list[int]",
        statement="Both lists are sorted in ascending order. Return one sorted list with all "
                  "their elements. Must work for any two sorted lists with no value in common, "
                  "including empty ones.",
        visible=[[[1, 4, 9], [2, 3]], [[], [5, 6]]],
        ambiguous=[[[1, 2], [2, 3]], [[3], [3]], [[1, 1], []], [[2, 5, 5], [5]]],
        dominio=lambda r: (lambda d, k: [sorted(d[:k]), sorted(d[k:])])(*(lambda d: (d, r.randint(0, len(d))))(distintos(r, r.randint(0, 9)))),
    ),
    dict(
        fn="most_frequent", ref=ref_most_frequent, opt=True,
        sello="most_frequent(xs: List[Int]) -> Option[Int]",
        python="def most_frequent(xs: list[int]) -> int | None",
        statement="Return the value that appears most often, or nothing for the empty list. Must "
                  "work for any list in which one value appears strictly more often than the rest.",
        visible=[[[1, 2, 2, 3]], [[]]],
        ambiguous=[[[1, 2]], [[3, 1, 3, 1]], [[9, 8, 7]], [[2, 2, 1, 1, 0]]],
        dominio=lambda r: (lambda xs, v: [xs + [v] * (max(xs.count(u) for u in xs + [v]) + 1)])(lista(r, r.randint(0, 5), 1, 4), r.randint(1, 4)),
    ),
    dict(
        fn="nth", ref=ref_nth, opt=True,
        sello="nth(xs: List[Int], i: Int) -> Option[Int]",
        python="def nth(xs: list[int], i: int) -> int | None",
        statement="Return the element at 0-based index i, or nothing if the index is past the "
                  "end. Must work for any list and any i >= 0.",
        visible=[[[5, 6, 7], 1], [[5, 6, 7], 3]],
        ambiguous=[[[1, 2, 3], -1], [[1, 2, 3], -3], [[1, 2, 3], -4], [[], -1]],
        dominio=lambda r: (lambda xs: [xs, r.randint(0, len(xs) + 1)])(lista(r)),
    ),
    dict(
        fn="power", ref=ref_power, opt=False,
        sello="power(base: Int, exp: Int) -> Int",
        python="def power(base: int, exp: int) -> int",
        statement="Return base raised to exp. Must work for any base and any exp >= 1.",
        visible=[[2, 10], [-3, 3]],
        ambiguous=[[0, 0], [5, 0], [2, -1], [-2, -2], [1, -5]],
        dominio=lambda r: [r.randint(-5, 5), r.randint(1, 8)],
    ),
    dict(
        fn="rotate_left", ref=ref_rotate_left, opt=False,
        sello="rotate_left(xs: List[Int], k: Int) -> List[Int]",
        python="def rotate_left(xs: list[int], k: int) -> list[int]",
        statement="Rotate the list to the left by k positions: the first k elements move to the "
                  "end. Must work for any list and any k between 0 and the length of the list.",
        visible=[[[1, 2, 3, 4], 1], [[1, 2, 3, 4], 3]],
        ambiguous=[[[1, 2, 3], 4], [[1, 2, 3], 7], [[1, 2, 3], -1], [[], 2], [[1, 2, 3, 4], -6]],
        dominio=lambda r: (lambda xs: [xs, r.randint(0, len(xs))])(lista(r)),
    ),
    dict(
        fn="second_largest", ref=ref_second_largest, opt=True,
        sello="second_largest(xs: List[Int]) -> Option[Int]",
        python="def second_largest(xs: list[int]) -> int | None",
        statement="Return the second largest value in the list, or nothing if there is none. "
                  "Must work for any list whose values are all different, including lists with "
                  "fewer than two elements.",
        visible=[[[3, 9, 1]], [[4]]],
        ambiguous=[[[5, 5, 3]], [[5, 5]], [[7, 7, 7]], [[1, 3, 3, 2]]],
        dominio=lambda r: [distintos(r)],
    ),
    dict(
        fn="zip_sum", ref=ref_zip_sum, opt=False,
        sello="zip_sum(xs: List[Int], ys: List[Int]) -> List[Int]",
        python="def zip_sum(xs: list[int], ys: list[int]) -> list[int]",
        statement="Add the two lists element by element. Must work for any two lists of the "
                  "same length, including empty ones.",
        visible=[[[1, 2, 3], [10, 20, 30]], [[], []]],
        ambiguous=[[[1, 2, 3], [1]], [[1], [1, 2, 3]], [[], [4, 5]], [[7, 8], []]],
        dominio=lambda r: (lambda n: [lista(r, n), lista(r, n)])(r.randint(0, 6)),
    ),
]


def neutro(v: object, opt: bool) -> object:
    """Valor Python -> JSON neutro del harness (Option como {"some": v} / null)."""
    if opt:
        return None if v is None else {"some": v}
    return v


def caso(p: dict, args: list, zona: str) -> dict:
    return {"args": args, "expect": neutro(p["ref"](*args), p["opt"]), "zone": zona}


def generar(p: dict, rng: random.Random) -> dict:
    vistos: set[str] = set()
    oraculo: list[dict] = []
    for a in p["ambiguous"]:
        oraculo.append(caso(p, a, "ambiguous"))
    intentos = 0
    while sum(1 for c in oraculo if c["zone"] == "domain") < N_DOMINIO and intentos < 500:
        intentos += 1
        a = p["dominio"](rng)
        k = json.dumps(a)
        if k in vistos or a in p["visible"]:
            continue
        vistos.add(k)
        oraculo.append(caso(p, a, "domain"))
    return {"fn": p["fn"], "statement": p["statement"], "sello": p["sello"], "python": p["python"],
            "option": p["opt"], "visible": [caso(p, a, "visible") for a in p["visible"]],
            "oracle": oraculo}


def main() -> int:
    SALIDA.mkdir(exist_ok=True)
    for p in PROBLEMAS:
        rng = random.Random(f"{SEMILLA}-{p['fn']}")
        d = generar(p, rng)
        (SALIDA / f"{p['fn']}.json").write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
        dom = sum(1 for c in d["oracle"] if c["zone"] == "domain")
        amb = len(d["oracle"]) - dom
        print(f"{p['fn']:<15} dominio {dom:>2}  ambigua {amb:>2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
