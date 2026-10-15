"""El contrato escrito por el mismo modelo que el cuerpo, y el aviso de ambigüedad tras aceptar
(issue #3): `python_propio` es la gemela en Python de la condición `sello`."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench"))
import harness3 as h3  # noqa: E402
import juez  # noqa: E402

P = {"fn": "count_greater", "python": "def count_greater(xs: list[int], t: int) -> int", "option": False,
     "statement": "Count the elements of xs greater than t.",
     "visible": [{"args": [[1, 5, 7], 4], "expect": 2, "zone": "visible"},
                 {"args": [[], 0], "expect": 0, "zone": "visible"}],
     "oracle": [{"args": [[3, 9], 2], "expect": 2, "zone": "domain"}]}

COTA = '''
def count_greater(xs: list[int], t: int) -> int:
    """
    post: __return__ >= 0
    post: __return__ <= len(xs)
    """
    return sum(1 for x in xs if x > t)
'''

FIJO = '''
def count_greater(xs: list[int], t: int) -> int:
    """
    post: __return__ == len([x for x in xs if x > t])
    """
    return sum(1 for x in xs if x > t)
'''


def responde(*codigos):
    """Un modelo de mentira que contesta, por orden, con estos programas."""
    it = iter(codigos)
    return lambda prompt, model: {"text": f"```python\n{next(it)}\n```", "cost": 0.0, "tokens_in": 0,
                                  "tokens_out": 0, "ms": 0}


def test_python_propio_sin_post_se_rechaza():
    sin = "def count_greater(xs: list[int], t: int) -> int:\n    return sum(1 for x in xs if x > t)\n"
    ok, fb, fase = h3.juez_debil(h3.PY_PROPIO, sin, P)
    assert not ok and fase == "contract" and "post:" in fb


def test_python_propio_comprueba_su_contrato_al_ejecutar():
    malo = FIJO.replace("return sum(1 for x in xs if x > t)", "return 0")
    r = h3.ejecutar(h3.PY_PROPIO, malo, P, P["oracle"])
    assert r[0]["result"] == juez.CAUGHT


def test_el_aviso_es_una_vuelta_y_si_su_respuesta_falla_queda_lo_aceptado(monkeypatch):
    roto = COTA.replace("return sum(1 for x in xs if x > t)", "return -1")
    monkeypatch.setattr(h3, "ask", responde(COTA, roto))
    r = h3.run_one(P, h3.PY_PROPIO, "haiku", 5, aviso=True)
    assert r["accepted_at"] == 1 and r["code"].strip() == COTA.strip()
    assert len(r["avisado"]) == 1 and "count_greater(" in r["avisado"][0]
    assert r["attempts"] == 2 and r["aviso_sustituye"] is False


def test_el_aviso_que_fija_el_contrato_lo_sustituye(monkeypatch):
    monkeypatch.setattr(h3, "ask", responde(COTA, FIJO))
    r = h3.run_one(P, h3.PY_PROPIO, "haiku", 5, aviso=True)
    assert r["code"].strip() == FIJO.strip() and r["aviso_sustituye"] is True


def test_sin_ambiguedad_no_hay_vuelta(monkeypatch):
    monkeypatch.setattr(h3, "ask", responde(FIJO))
    r = h3.run_one(P, h3.PY_PROPIO, "haiku", 5, aviso=True)
    assert r["attempts"] == 1 and r["avisado"] == []


def test_los_contratos_propios_de_python_se_cargan_para_la_prueba_de_literales(tmp_path):
    f = tmp_path / "juez.jsonl"
    f.write_text(json.dumps({"problem": "count_greater", "cond": h3.PY_PROPIO, "model": "haiku",
                             "code": FIJO, "accepted_at": 1}) + "\n")
    assert h3.cargar_contratos(f)["count_greater"]["code"] == FIJO
