"""El juez imperfecto: la regla de clasificación por zonas y la coherencia de la batería.

Es lógica de negocio del experimento: si la regla se tuerce, la métrica miente.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench"))
import generar_ambiguos as gen  # noqa: E402
import juez  # noqa: E402


# ---------- clasificación ----------

@pytest.mark.parametrize("zona,resultado,esperado", [
    ("domain", juez.OK, juez.CORRECTO),
    ("domain", juez.WRONG, juez.SILENCIOSO),
    ("domain", juez.REJECT, juez.RUIDOSO),     # rechazo indebido: el enunciado lo exigía
    ("domain", juez.CAUGHT, juez.RUIDOSO),     # mal, pero el contrato lo vio
    ("ambiguous", juez.OK, juez.CORRECTO),
    ("ambiguous", juez.WRONG, juez.SILENCIOSO),  # lo que nadie ve: cuenta
    ("ambiguous", juez.REJECT, juez.DECLARADO),
    ("ambiguous", juez.CAUGHT, juez.DECLARADO),
])
def test_clasificar(zona, resultado, esperado):
    assert juez.clasificar(zona, resultado) == esperado


def test_resultado_sello_distingue_e201_de_e300():
    assert juez.resultado_sello(None) == juez.OK
    assert juez.resultado_sello({"call": "f(1)", "expected": "2", "got": "3"}) == juez.WRONG
    assert juez.resultado_sello({"call": "f(1)", "error": {"code": "E201"}}) == juez.CAUGHT
    assert juez.resultado_sello({"call": "f(1)", "error": {"code": "E300"}}) == juez.REJECT
    assert juez.resultado_sello({"call": "f(1)", "error": {"code": "E500"}}) == juez.REJECT


def test_resultado_python():
    assert juez.resultado_python("ok") == juez.OK
    assert juez.resultado_python("wrong") == juez.WRONG
    assert juez.resultado_python("assert") == juez.CAUGHT
    assert juez.resultado_python("raise") == juez.REJECT
    assert juez.resultado_python("timeout") == juez.REJECT


def test_contar_separa_zonas_y_cuenta_cazados():
    casos = [
        {"zone": "domain", "result": juez.OK},
        {"zone": "domain", "result": juez.WRONG},
        {"zone": "domain", "result": juez.CAUGHT},
        {"zone": "ambiguous", "result": juez.WRONG},
        {"zone": "ambiguous", "result": juez.REJECT},
        {"zone": "ambiguous", "result": juez.CAUGHT},
    ]
    c = juez.contar(casos)
    assert (c["dom_total"], c["dom_correcto"], c["dom_silencioso"], c["dom_ruidoso"]) == (3, 1, 1, 1)
    assert (c["amb_total"], c["amb_silencioso"], c["amb_declarado"]) == (3, 1, 2)
    assert c["cazados"] == 2
    assert c["silenciosos"] == 2


# ---------- la batería ----------

@pytest.mark.parametrize("p", gen.PROBLEMAS, ids=lambda p: p["fn"])
def test_referencia_pasa_sus_ejemplos_visibles_y_es_determinista(p):
    a = gen.generar(p, random.Random("x"))
    b = gen.generar(p, random.Random("x"))
    assert a == b
    zonas = {c["zone"] for c in a["oracle"]}
    assert zonas == {"domain", "ambiguous"}, "cada problema necesita las dos zonas"
    assert sum(1 for c in a["oracle"] if c["zone"] == "domain") == gen.N_DOMINIO
    visibles = [c["args"] for c in a["visible"]]
    assert all(c["args"] not in visibles for c in a["oracle"]), "el oráculo no repite lo visible"


def test_los_json_commiteados_coinciden_con_el_generador():
    """Regla 3: los casos se generan una vez y se commitean. Si alguien toca el generador
    sin regenerar (o al revés), este test lo dice."""
    for p in gen.PROBLEMAS:
        f = gen.SALIDA / f"{p['fn']}.json"
        if not f.exists():
            pytest.skip("batería no generada todavía")
        en_disco = json.loads(f.read_text())
        assert en_disco == gen.generar(p, random.Random(f"{gen.SEMILLA}-{p['fn']}"))
