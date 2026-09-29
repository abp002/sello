"""Contratos a ciegas: el instrumento que mide un contrato y el juez débil de quien lo escribe.

Lógica del experimento 'El contrato se puede escribir sin el cuerpo'. Si la prueba de literales
contara mal, la pregunta 1 mediría otra cosa; si el juez débil dejara pasar un cuerpo, el
contrato ya no sería a ciegas; si `harness3` no cargara un contrato que compila pero no pasó su
juez débil, se incumpliría la regla 1.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench"))
import contrato as ct  # noqa: E402
import contratar  # noqa: E402
import harness3  # noqa: E402
import literales as lit  # noqa: E402

# Un problema de juguete con la forma de bench/ambiguos: el siguiente del oráculo da el
# literal incorrecto, y el caso 3 (2 -> 3) repite respuesta con su siguiente y se salta.
INC = {"fn": "inc", "sello": "inc(n: Int) -> Int", "statement": "Add one to n, for n >= 0.",
       "visible": [{"args": [1], "expect": 2, "zone": "visible"}, {"args": [4], "expect": 5, "zone": "visible"}],
       "oracle": [{"args": [0], "expect": 1, "zone": "domain"}, {"args": [5], "expect": 6, "zone": "domain"},
                  {"args": [2], "expect": 3, "zone": "domain"}, {"args": [-2], "expect": 3, "zone": "ambiguous"}]}


def contrato(ensures: str, requires: str = "n >= 0", cuerpo: str = "sorry", helpers: str = "") -> str:
    return (helpers + f"""
fn inc(n: Int) -> Int
  requires {requires}
  ensures {ensures}
  effects pure
  example inc(1) == 2
{{ {cuerpo} }}
""")


def medir(src: str) -> dict:
    return lit.medir(ct.extraer(src, "inc"), INC)


# ---------- la prueba de literales ----------

def test_un_contrato_de_contenido_admite_lo_correcto_y_caza_lo_incorrecto():
    m = medir(contrato("result == n + 1"))
    assert (m["dominio"], m["rechaza_correcto"], m["requires_fuera"]) == (3, 0, 0)
    assert (m["incorrectos"], m["admite_incorrecto"]) == (2, 0)  # 2 -> 3 y su siguiente, 3: se salta
    assert (m["ambiguos"], m["ambiguos_rechazados"]) == (1, 1)  # -2 no cumple el requires
    assert m["solo_cotas"] is True  # cotas.py mide la forma: una igualdad aritmética cuenta como cota
    siguiente = """
fn es_siguiente(a: Int, b: Int) -> Bool
  requires a >= 0
  ensures result == (b == a + 1)
  effects pure
  example es_siguiente(1, 2) == true
{ b == a + 1 }
"""
    m = medir(contrato("es_siguiente(n, result)", helpers=siguiente))
    assert (m["rechaza_correcto"], m["admite_incorrecto"], m["solo_cotas"]) == (0, 0, False)


def test_una_cota_admite_lo_incorrecto():
    m = medir(contrato("result > n"))
    assert (m["rechaza_correcto"], m["admite_incorrecto"], m["solo_cotas"]) == (0, 1, True)  # 0 -> 6 pasa; 5 -> 3 no


def test_rechazar_lo_correcto_es_E201_y_un_requires_estrecho_va_aparte():
    m = medir(contrato("result == n + 2"))
    assert m["rechaza_correcto"] == 3
    m = medir(contrato("result == n + 1", requires="n >= 1"))
    assert (m["rechaza_correcto"], m["requires_fuera"]) == (0, 1)  # inc(0)


def test_los_ejemplos_de_la_principal_no_corren_y_los_de_los_helpers_si():
    """El cuerpo constante no pasaría `example inc(1) == 2`; un helper roto sí se nota."""
    assert medir(contrato("result == n + 1", cuerpo="n * 7"))["rechaza_correcto"] == 0
    roto = """
fn uno_mas(a: Int, b: Int) -> Bool
  requires a >= 0
  ensures result == (b == a + 1)
  effects pure
  example uno_mas(1, 2) == false
{ b == a + 1 }
"""
    try:
        medir(contrato("uno_mas(n, result)", helpers=roto))
    except lit.SelloError as e:
        assert e.code == "E200"
    else:
        raise AssertionError("un helper que falla su ejemplo tenía que romper la medición")


# ---------- el juez débil de quien escribe el contrato ----------

def test_el_juez_debil_pide_solo_el_contrato():
    assert contratar.juez_debil(contrato("result == n + 1", cuerpo="n + 1"), INC)[2] == "body"
    assert contratar.juez_debil(contrato("result == n + 1"), INC) == (True, "", "ok")
    assert contratar.juez_debil(contrato("result == nn"), INC)[2] == "compile"


def test_el_juez_debil_ensena_el_ejemplo_visible_que_el_contrato_rechaza():
    ok, feedback, fase = contratar.juez_debil(contrato("result == n + 2"), INC)
    assert (ok, fase) == (False, "examples")
    rechazos = json.loads(feedback)["rejected"]
    assert [(r["call"], r["correct_result"], r["error"]["code"]) for r in rechazos] == [("inc(1)", "2", "E201"), ("inc(4)", "5", "E201")]


def test_compila_juzga_el_contrato_aunque_traiga_cuerpo():
    assert contratar.compila(contrato("result == n + 1", cuerpo="n + 1"), "inc")
    assert not contratar.compila(contrato("result == nn"), "inc")
    assert not contratar.compila(contrato("result == n + 1"), "otra")


# ---------- harness3 carga lo que dice la regla 1 ----------

def test_harness3_carga_los_contratos_que_compilan_aceptados_o_no(tmp_path):
    filas = [{"problem": "a", "cond": "contrato", "model": "sonnet", "accepted_at": None, "compila": True, "code": "A"},
             {"problem": "b", "cond": "contrato", "model": "sonnet", "accepted_at": None, "compila": False, "code": "B"},
             {"problem": "c", "cond": "contrato", "model": "sonnet", "accepted_at": 2, "compila": True, "code": "C"}]
    f = tmp_path / "contratos-x-sonnet.jsonl"
    f.write_text("".join(json.dumps(r) + "\n" for r in filas))
    assert sorted(harness3.cargar_contratos(f)) == ["a", "c"]
    assert harness3.de_contratar(f)


def test_harness3_no_corre_un_problema_sin_contrato():
    r = harness3.run_one(INC, harness3.CONTRATO, "haiku", 5, contratos={})
    assert r["sin_contrato"] and r["accepted_at"] is None and r["attempts"] == 0
