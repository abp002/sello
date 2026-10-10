"""El veredicto del probador no depende de cómo se llamen las funciones (SEL-2).

Nota 'El probador nombra cada función por su hash'. Regresión de la medición de SEL-1: DH0104
(vericoding, sonnet, intento 1) probaba `Build` e `Insert` con los nombres del fichero y los dejaba
en nivel 1 renombrados a `f_<hash>`, que es como los enlaza el almacén. El mismo hash quedaba
certificado en un nivel u otro según el fichero del que viniera.
"""

from __future__ import annotations

import sys
from pathlib import Path

import z3

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench"))
import nombres  # noqa: E402

from sello.compile import check_source  # noqa: E402
from sello.hash import hash_program, short  # noqa: E402
from sello.parser import parse  # noqa: E402
from sello.prover import Translator  # noqa: E402

DH0104 = (Path(__file__).parent / "datos" / "dh0104.sello").read_text()


def niveles(code: str, vuelta: dict[str, str]) -> dict[str, int]:
    r = check_source(code)
    assert r["ok"], r
    return {vuelta.get(f["name"], f["name"]): f.get("level", 1) for f in r["functions"]}


def test_el_mismo_programa_con_otros_nombres_da_los_mismos_niveles():
    base = niveles(DH0104, {})  # antes, Build e Insert en 2 con estos nombres y en 1 con los del almacén
    for esquema in ("H", "X"):
        code, vuelta = nombres.variante(DH0104, esquema)
        assert niveles(code, vuelta) == base, esquema


def test_a_z3_llegan_los_nombres_del_hash():
    program = parse(DH0104)
    fn = next(f for f in program.fns if f.name == "Build")
    tr = Translator(program, fn, z3.Context())
    h = hash_program(program)
    assert str(tr.uf(next(f for f in program.fns if f.name == "Insert"))) == f"fn!f_{short(h['Insert'])}"
