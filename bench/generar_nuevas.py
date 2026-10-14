#!/usr/bin/env python3
"""Genera la batería del experimento decisivo (SEL-9, SEL-15): `bench/nuevas/*.json`.

El mismo molde que `generar_ambiguos.py`: enunciado con un dominio obligatorio declarado y, en
casi todas, una zona ambigua (lo que el enunciado calla); dos casos visibles; casos del oráculo
calculados por una referencia en Python con semilla fija. La política de la referencia en la zona
ambigua es arbitraria y está escrita aquí; la suerte de acertarla es la misma para los dos
lenguajes. Ninguna repite las de `problemas/`, `problemas2/`, `dificiles/` ni `ambiguos/`.

    .venv/bin/python bench/generar_nuevas.py

Se ejecuta una vez y el resultado se commitea antes de la primera corrida.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

SALIDA = Path(__file__).resolve().parent / "nuevas"
SEMILLA = 20261015
N_DOMINIO = 25


def lista(rng: random.Random, n: int | None = None, lo: int = -9, hi: int = 9) -> list[int]:
    if n is None:
        n = rng.randint(0, 7)
    return [rng.randint(lo, hi) for _ in range(n)]


def distintos(rng: random.Random, n: int | None = None, lo: int = -20, hi: int = 20) -> list[int]:
    if n is None:
        n = rng.randint(0, 7)
    return rng.sample(range(lo, hi + 1), n)


# ---------- referencias ----------

def ref_digit_sum(n):
    return sum(int(c) for c in str(abs(n)))


def ref_count_greater(xs, t):
    return sum(1 for v in xs if v > t)


def ref_last_index_of(xs, x):
    return len(xs) - 1 - xs[::-1].index(x) if x in xs else -1


def ref_kth_smallest(xs, k):
    return sorted(xs)[k - 1] if 1 <= k <= len(xs) else 0


def ref_prefix_sums(xs):
    out, acc = [], 0
    for v in xs:
        acc += v
        out.append(acc)
    return out


def ref_is_sorted(xs):
    return all(xs[i] <= xs[i + 1] for i in range(len(xs) - 1))


def ref_count_pairs_sum(xs, t):
    return sum(1 for i in range(len(xs)) for j in range(i + 1, len(xs)) if xs[i] + xs[j] == t)


def ref_first_missing(xs):
    k = 1
    while k in xs:
        k += 1
    return k


def ref_majority(xs):
    for v in xs:
        if 2 * xs.count(v) > len(xs):
            return v
    return None


def ref_binary_search(xs, x):
    return xs.index(x) if x in xs else None


def ref_interleave(xs, ys):
    out = []
    for a, b in zip(xs, ys):
        out += [a, b]
    n = min(len(xs), len(ys))
    return out + xs[n:] + ys[n:]


def ref_remove_all(xs, x):
    return [v for v in xs if v != x]


def ref_take_while_pos(xs):
    out = []
    for v in xs:
        if v <= 0:
            break
        out.append(v)
    return out


def ref_collatz_steps(n):
    if n <= 0:
        return 0
    k = 0
    while n != 1:
        n = n // 2 if n % 2 == 0 else 3 * n + 1
        k += 1
    return k


def ref_fib(n):
    if n < 0:
        return 0
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def ref_count_divisors(n):
    return sum(1 for d in range(1, n + 1) if n % d == 0) if n >= 1 else 0


def ref_is_prime(n):
    return n >= 2 and all(n % d for d in range(2, n))


def ref_max_gap(xs):
    return max((abs(xs[i + 1] - xs[i]) for i in range(len(xs) - 1)), default=0)


def ref_evens_first(xs):
    return [v for v in xs if v % 2 == 0] + [v for v in xs if v % 2 != 0]


def ref_range_list(a, b):
    return list(range(a, b + 1))


def ref_min_index(xs):
    return xs.index(min(xs)) if xs else -1


def ref_replace_all(xs, a, b):
    return [b if v == a else v for v in xs]


def ref_balance(xs):
    bal = 0
    for v in xs:
        if bal + v >= 0:
            bal += v
    return bal


def ref_median_odd(xs):
    return sorted(xs)[(len(xs) - 1) // 2] if xs else 0


# ---------- problemas ----------
# statement: dominio obligatorio declarado. Lo que no dice es la zona ambigua.
# visible: dos casos de camino feliz que van en el enunciado (juez débil).
# ambiguous: entradas de la zona ambigua, a mano. dominio: generador aleatorio.

PROBLEMAS = [
    dict(
        fn="digit_sum", ref=ref_digit_sum, opt=False,
        sello="digit_sum(n: Int) -> Int",
        python="def digit_sum(n: int) -> int",
        statement="Return the sum of the decimal digits of n. Must work for any n >= 0.",
        visible=[[123], [0]],
        ambiguous=[[-5], [-123], [-90]],
        dominio=lambda r: [r.choice([r.randint(0, 9), r.randint(10, 999), r.randint(1000, 99999)])],
    ),
    dict(
        fn="count_greater", ref=ref_count_greater, opt=False,
        sello="count_greater(xs: List[Int], t: Int) -> Int",
        python="def count_greater(xs: list[int], t: int) -> int",
        statement="Return how many elements of xs are strictly greater than t. Must work for any "
                  "list and any t.",
        visible=[[[1, 5, 3, 8], 3], [[], 0]],
        ambiguous=[],
        dominio=lambda r: [lista(r), r.randint(-9, 9)],
    ),
    dict(
        fn="last_index_of", ref=ref_last_index_of, opt=False,
        sello="last_index_of(xs: List[Int], x: Int) -> Int",
        python="def last_index_of(xs: list[int], x: int) -> int",
        statement="Return the 0-based position of the last occurrence of x in xs. Must work for "
                  "any list that contains x at least once.",
        visible=[[[4, 7, 4, 9], 4], [[5], 5]],
        ambiguous=[[[], 3], [[1, 2], 5], [[0, 0], 1]],
        dominio=lambda r: (lambda xs: [xs, r.choice(xs)])(lista(r, r.randint(1, 7), 1, 4)),
    ),
    dict(
        fn="kth_smallest", ref=ref_kth_smallest, opt=False,
        sello="kth_smallest(xs: List[Int], k: Int) -> Int",
        python="def kth_smallest(xs: list[int], k: int) -> int",
        statement="Return the k-th smallest value of xs, counting from k = 1 for the smallest. "
                  "Must work for any list whose values are all different and any k from 1 to the "
                  "length of the list.",
        visible=[[[7, 2, 9, 4], 1], [[7, 2, 9, 4], 3]],
        ambiguous=[[[3, 3, 1], 2], [[5, 1, 5, 1], 3], [[4, 2], 0], [[4, 2], 3], [[], 1]],
        dominio=lambda r: (lambda xs: [xs, r.randint(1, len(xs))])(distintos(r, r.randint(1, 7))),
    ),
    dict(
        fn="prefix_sums", ref=ref_prefix_sums, opt=False,
        sello="prefix_sums(xs: List[Int]) -> List[Int]",
        python="def prefix_sums(xs: list[int]) -> list[int]",
        statement="Return the running totals of xs: the element at position i is the sum of the "
                  "first i + 1 elements. Must work for any list, including the empty one.",
        visible=[[[1, 2, 3]], [[]]],
        ambiguous=[],
        dominio=lambda r: [lista(r)],
    ),
    dict(
        fn="is_sorted", ref=ref_is_sorted, opt=False,
        sello="is_sorted(xs: List[Int]) -> Bool",
        python="def is_sorted(xs: list[int]) -> bool",
        statement="Return whether every element is less than or equal to the next one. Must work "
                  "for any list, including the empty one.",
        visible=[[[1, 2, 2, 5]], [[3, 1]]],
        ambiguous=[],
        dominio=lambda r: [sorted(lista(r, None, 1, 5)) if r.random() < 0.4 else lista(r, None, 1, 5)],
    ),
    dict(
        fn="count_pairs_sum", ref=ref_count_pairs_sum, opt=False,
        sello="count_pairs_sum(xs: List[Int], t: Int) -> Int",
        python="def count_pairs_sum(xs: list[int], t: int) -> int",
        statement="Return how many pairs of different positions i < j have xs[i] + xs[j] == t. "
                  "Must work for any list whose values are all different and any t.",
        visible=[[[1, 2, 3, 4], 5], [[1, 2], 9]],
        ambiguous=[[[2, 2, 2], 4], [[1, 3, 1, 3], 4], [[5, 5], 10]],
        dominio=lambda r: (lambda xs: [xs, r.choice([r.randint(-10, 10)] + [a + b for a in xs for b in xs if a != b])])(distintos(r, None, -9, 9)),
    ),
    dict(
        fn="first_missing", ref=ref_first_missing, opt=False,
        sello="first_missing(xs: List[Int]) -> Int",
        python="def first_missing(xs: list[int]) -> int",
        statement="Return the smallest positive integer that does not appear in xs. Must work for "
                  "any list of positive integers, including the empty one.",
        visible=[[[1, 2, 4]], [[3, 5]]],
        ambiguous=[[[0, 1, 2]], [[-1, 1]], [[0]], [[-3, -2]]],
        dominio=lambda r: [lista(r, None, 1, 6)],
    ),
    dict(
        fn="majority", ref=ref_majority, opt=True,
        sello="majority(xs: List[Int]) -> Option[Int]",
        python="def majority(xs: list[int]) -> int | None",
        statement="Return the value that appears in more than half of the positions of xs, or "
                  "nothing if no value does. Must work for any list, including the empty one.",
        visible=[[[3, 1, 3, 3]], [[1, 2]]],
        ambiguous=[],
        dominio=lambda r: [lista(r, r.randint(0, 7), 1, 3)],
    ),
    dict(
        fn="binary_search", ref=ref_binary_search, opt=True,
        sello="binary_search(xs: List[Int], x: Int) -> Option[Int]",
        python="def binary_search(xs: list[int], x: int) -> int | None",
        statement="xs is sorted in strictly ascending order. Return the 0-based position of x in "
                  "xs, or nothing if x is not in xs. Must work for any strictly ascending list and "
                  "any x.",
        visible=[[[1, 4, 6, 9], 6], [[1, 4, 6, 9], 5]],
        ambiguous=[[[3, 1, 2], 1], [[2, 2, 5], 2], [[9, 4, 1], 9], [[5, 5], 5]],
        dominio=lambda r: (lambda xs: [xs, r.choice(xs + [r.randint(-20, 20)]) if xs else r.randint(-20, 20)])(sorted(distintos(r))),
    ),
    dict(
        fn="interleave", ref=ref_interleave, opt=False,
        sello="interleave(xs: List[Int], ys: List[Int]) -> List[Int]",
        python="def interleave(xs: list[int], ys: list[int]) -> list[int]",
        statement="Return the elements of xs and ys alternately, starting with the first element "
                  "of xs. Must work for any two lists of the same length, including empty ones.",
        visible=[[[1, 2, 3], [7, 8, 9]], [[], []]],
        ambiguous=[[[1, 2, 3], [9]], [[1], [7, 8, 9]], [[], [4, 5]], [[6, 7], []]],
        dominio=lambda r: (lambda n: [lista(r, n), lista(r, n)])(r.randint(0, 5)),
    ),
    dict(
        fn="remove_all", ref=ref_remove_all, opt=False,
        sello="remove_all(xs: List[Int], x: Int) -> List[Int]",
        python="def remove_all(xs: list[int], x: int) -> list[int]",
        statement="Return xs without any occurrence of x, keeping the other elements in their "
                  "order. Must work for any list and any x.",
        visible=[[[1, 2, 1, 3], 1], [[4, 5], 9]],
        ambiguous=[],
        dominio=lambda r: [lista(r, None, 1, 4), r.randint(1, 4)],
    ),
    dict(
        fn="take_while_pos", ref=ref_take_while_pos, opt=False,
        sello="take_while_pos(xs: List[Int]) -> List[Int]",
        python="def take_while_pos(xs: list[int]) -> list[int]",
        statement="Return the longest prefix of xs whose elements are all greater than zero. Must "
                  "work for any list, including the empty one.",
        visible=[[[3, 1, -2, 5]], [[0, 4]]],
        ambiguous=[],
        dominio=lambda r: [lista(r, None, -3, 9)],
    ),
    dict(
        fn="collatz_steps", ref=ref_collatz_steps, opt=False,
        sello="collatz_steps(n: Int) -> Int",
        python="def collatz_steps(n: int) -> int",
        statement="Starting from n, repeatedly halve it if it is even or replace it with 3n + 1 if "
                  "it is odd, until it reaches 1. Return the number of steps. Must work for any "
                  "n >= 1.",
        visible=[[6], [1]],
        ambiguous=[[0], [-1], [-6]],
        dominio=lambda r: [r.randint(1, 60)],
    ),
    dict(
        fn="fib", ref=ref_fib, opt=False,
        sello="fib(n: Int) -> Int",
        python="def fib(n: int) -> int",
        statement="Return the n-th Fibonacci number, with fib(0) = 0 and fib(1) = 1. Must work for "
                  "any n >= 0.",
        visible=[[10], [1]],
        ambiguous=[[-1], [-2], [-10]],
        dominio=lambda r: [r.randint(0, 30)],
    ),
    dict(
        fn="count_divisors", ref=ref_count_divisors, opt=False,
        sello="count_divisors(n: Int) -> Int",
        python="def count_divisors(n: int) -> int",
        statement="Return how many positive integers divide n exactly. Must work for any n >= 1.",
        visible=[[12], [7]],
        ambiguous=[[0], [-6], [-1]],
        dominio=lambda r: [r.randint(1, 100)],
    ),
    dict(
        fn="is_prime", ref=ref_is_prime, opt=False,
        sello="is_prime(n: Int) -> Bool",
        python="def is_prime(n: int) -> bool",
        statement="Return whether n is a prime number. Must work for any n >= 2.",
        visible=[[13], [15]],
        ambiguous=[[1], [0], [-7]],
        dominio=lambda r: [r.randint(2, 100)],
    ),
    dict(
        fn="max_gap", ref=ref_max_gap, opt=False,
        sello="max_gap(xs: List[Int]) -> Int",
        python="def max_gap(xs: list[int]) -> int",
        statement="Return the largest absolute difference between two adjacent elements of xs. "
                  "Must work for any list with at least two elements.",
        visible=[[[1, 7, 4]], [[5, 5]]],
        ambiguous=[[[]], [[3]], [[-8]]],
        dominio=lambda r: [lista(r, r.randint(2, 7))],
    ),
    dict(
        fn="evens_first", ref=ref_evens_first, opt=False,
        sello="evens_first(xs: List[Int]) -> List[Int]",
        python="def evens_first(xs: list[int]) -> list[int]",
        statement="Return the even elements of xs followed by the odd ones, each group in its "
                  "original order. Must work for any list, including the empty one.",
        visible=[[[1, 2, 3, 4]], [[5, 7]]],
        ambiguous=[],
        dominio=lambda r: [lista(r)],
    ),
    dict(
        fn="range_list", ref=ref_range_list, opt=False,
        sello="range_list(a: Int, b: Int) -> List[Int]",
        python="def range_list(a: int, b: int) -> list[int]",
        statement="Return the integers from a to b, both included, in ascending order. Must work "
                  "for any a and b with a <= b.",
        visible=[[2, 5], [-1, -1]],
        ambiguous=[[3, 1], [0, -2], [5, 4]],
        dominio=lambda r: (lambda a: [a, a + r.randint(0, 8)])(r.randint(-9, 9)),
    ),
    dict(
        fn="min_index", ref=ref_min_index, opt=False,
        sello="min_index(xs: List[Int]) -> Int",
        python="def min_index(xs: list[int]) -> int",
        statement="Return the 0-based position of the first occurrence of the smallest element of "
                  "xs. Must work for any non-empty list.",
        visible=[[[4, 1, 3, 1]], [[2]]],
        ambiguous=[[[]]],
        dominio=lambda r: [lista(r, r.randint(1, 7), -4, 4)],
    ),
    dict(
        fn="replace_all", ref=ref_replace_all, opt=False,
        sello="replace_all(xs: List[Int], a: Int, b: Int) -> List[Int]",
        python="def replace_all(xs: list[int], a: int, b: int) -> list[int]",
        statement="Return xs with every occurrence of a replaced by b. Must work for any list and "
                  "any a and b.",
        visible=[[[1, 2, 1], 1, 7], [[3], 4, 5]],
        ambiguous=[],
        dominio=lambda r: [lista(r, None, 1, 4), r.randint(1, 4), r.randint(-5, 5)],
    ),
    dict(
        fn="balance", ref=ref_balance, opt=False,
        sello="balance(xs: List[Int]) -> Int",
        python="def balance(xs: list[int]) -> int",
        statement="xs is a list of transactions applied in order to an account that starts at 0: "
                  "a positive amount is a deposit and a negative one a withdrawal. A withdrawal "
                  "that would leave the balance below 0 is skipped. Return the final balance. Must "
                  "work for any list of non-zero amounts.",
        visible=[[[10, -3, -20, 5]], [[-5, 2]]],
        ambiguous=[[[0]], [[3, 0, -3]], [[0, -1]]],
        dominio=lambda r: [[v if v else 1 for v in lista(r, None, -9, 9)]],
    ),
    dict(
        fn="median_odd", ref=ref_median_odd, opt=False,
        sello="median_odd(xs: List[Int]) -> Int",
        python="def median_odd(xs: list[int]) -> int",
        statement="Return the median of xs: the value that would be in the middle if xs were "
                  "sorted. Must work for any list of odd length whose values are all different.",
        visible=[[[5, 1, 3]], [[8]]],
        ambiguous=[[[]], [[4, 1]], [[2, 2, 1]], [[9, 1, 5, 3]]],
        dominio=lambda r: [distintos(r, r.choice([1, 3, 5, 7]))],
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
    while sum(1 for c in oraculo if c["zone"] == "domain") < N_DOMINIO and intentos < 2000:
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
        print(f"{p['fn']:<16} dominio {dom:>2}  ambigua {amb:>2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
