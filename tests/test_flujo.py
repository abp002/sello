"""El flujo contrato→cuerpo por el almacén y el MCP: lo que el instrumento lee del almacén y de la traza.

Lógica del experimento 'Un hueco se rellena por el MCP igual que en el banco'. Si `programa_de`
reconstruyera por el alias de ahora, el oráculo juzgaría otra función que la guardada. Si
`relleno` confundiera un escape con otro nombre con un relleno, contaría como entregado lo que no
lo está. Si la traza se leyera mal, los E103 y los intentos serían otros.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench"))
import flujo  # noqa: E402
import mutantes  # noqa: E402

from sello.errors import SelloError  # noqa: E402
from sello.hash import hash_program  # noqa: E402
from sello.parser import parse  # noqa: E402
from sello.store import Store  # noqa: E402

POS_V1 = """
fn pos(n: Int) -> Bool
  requires 1 == 1
  ensures result == (n > 0)
  effects pure
  example pos(3) == true
{ n > 0 }
"""

POS_V2 = POS_V1.replace("n > 0", "n >= 0")

INC = """
fn inc(n: Int) -> Int
  requires pos(n)
  ensures result == n + 1
  effects pure
  example inc(1) == 2
{ n + 1 }
"""

# Su cierre tiene dos `pos` distintos: el de su cuerpo (v2, por el alias de ahora) y el del
# requires de `inc` (v1, por hash).
G = """
fn g(n: Int) -> Bool
  requires n > 0
  ensures result == (inc(n) > 1)
  effects pure
  example g(1) == true
{ pos(inc(n)) }
"""


def test_programa_de_toma_el_cierre_por_hash_y_no_por_el_alias_de_ahora(tmp_path):
    s = Store(tmp_path / "s.db")
    s.add(POS_V1 + INC)
    h = s.resolve("inc")
    s.add(POS_V2)  # el alias `pos` pasa a otra función
    texto, _ = flujo.programa_de(s, h)
    assert "n > 0" in texto and "n >= 0" not in texto
    assert hash_program(parse(texto))["inc"] == h


def test_programa_de_separa_dos_funciones_del_cierre_con_el_mismo_nombre(tmp_path):
    s = Store(tmp_path / "s.db")
    s.add(POS_V1 + INC)
    s.add(POS_V2)
    s.add(G)
    h = s.resolve("g")
    texto, nombres = flujo.programa_de(s, h)
    assert texto.count("fn f_") == 2 and "fn g(" in texto and "fn inc(" in texto
    assert nombres[h] == "g"


def test_programa_de_da_a_la_raiz_el_nombre_que_se_pide(tmp_path):
    # El mismo hash se guardó antes con otro nombre: el oráculo llama por el nombre del problema.
    s = Store(tmp_path / "s.db")
    s.add(POS_V1 + INC.replace("inc", "inc2"))
    s.add(INC)
    h = s.resolve("inc")
    assert s.resolve("inc2") == h
    texto, _ = flujo.programa_de(s, h, "inc")
    assert "fn inc(" in texto and "inc2" not in texto


def test_el_almacen_dice_si_el_cuerpo_rellena_el_hueco_del_otro_autor(tmp_path):
    s = Store(tmp_path / "s.db")
    # El control carga un contrato extraído de una solución con cuerpo: queda como hueco.
    hueco = flujo.cargar_hueco(s, POS_V1 + INC, "inc", "sonnet")
    assert flujo.hueco_de(s, "inc") == hueco and flujo.relleno(s, "inc", hueco) is None
    # Implementarlo con otro nombre no lo rellena: el nombre del problema sigue en el hueco.
    s.add(INC.replace("inc", "inc_mio"), author="haiku")
    assert flujo.relleno(s, "inc", hueco) is None and flujo.hueco_de(s, "inc") == hueco
    # Otro contrato con el mismo nombre: E103, y el hueco sigue donde estaba.
    with pytest.raises(SelloError) as e:
        s.add(INC.replace("result == n + 1", "result > n"), author="haiku")
    assert e.value.code == "E103" and flujo.hueco_de(s, "inc") == hueco
    s.add(INC, author="haiku")
    impl = flujo.relleno(s, "inc", hueco)
    assert impl not in (None, hueco) and flujo.hueco_de(s, "inc") is None
    assert flujo._nombres_de(s, "haiku") == ["inc", "inc_mio"]


def test_no_rellena_el_hueco_lo_que_el_nombre_tenga_con_otro_contrato(tmp_path):
    # El dueño del contrato puede cambiarlo, y con cuerpo. El nombre deja de estar en el hueco, pero
    # lo que tiene no lo rellena: si la guarda fallara, un contrato cambiado no contaría como entrega.
    s = Store(tmp_path / "s.db")
    hueco = flujo.cargar_hueco(s, POS_V1 + INC, "inc", "sonnet")
    s.add(INC.replace("result == n + 1", "result > n"), author="sonnet")
    assert flujo.hueco_de(s, "inc") is None and flujo.relleno(s, "inc", hueco) is None


def _uso(*llamadas: tuple) -> dict:
    """Un mensaje del agente con una o varias llamadas (id, tool, entrada): van en paralelo."""
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": i, "name": f"mcp__sello__{t}", "input": e} for i, t, e in llamadas]}}


def _res(*respuestas: tuple) -> dict:
    """Las respuestas (id, dict) de un mensaje, en el orden en que llegan."""
    return {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": i, "content": [{"type": "text", "text": json.dumps(d)}]}
        for i, d in respuestas]}}


IMPL = "b" * 64


def test_la_traza_cuenta_los_programas_los_e103_y_donde_se_acepto(tmp_path):
    eventos = [
        _uso(("1", "sello_spec", {})), _res(("1", {"ok": True, "spec": "..."})),
        _uso(("2", "sello_sig", {"name": "inc"})), _res(("2", {"ok": True})),
        _uso(("3", "sello_check", {"source": "A"})), _res(("3", {"ok": True})),
        _uso(("4", "sello_add", {"source": "A"})), _res(("4", {"ok": False, "error": {"code": "E103"}})),
        # dos en paralelo, y las respuestas llegan en el otro orden
        _uso(("5", "sello_view", {"name": "inc"}), ("6", "sello_add", {"source": "B"})),
        _res(("6", {"ok": False, "error": {"code": "E103"}}), ("5", {"ok": True, "source": "..."})),
        _uso(("7", "sello_add", {"source": "C"})), _res(("7", {"ok": True, "added": [
            {"name": "aux", "hash": "a" * 12}, {"name": "inc", "hash": IMPL[:12], "implements": "c" * 12}]})),
        _uso(("8", "sello_check", {"source": "D"})),  # la sesión se cortó antes de la respuesta
        {"type": "result", "subtype": "error_max_turns", "num_turns": 30, "total_cost_usd": 0.01,
         "usage": {"output_tokens": 10}},
    ]
    traza = tmp_path / "t.jsonl"
    traza.write_text("".join(json.dumps(e) + "\n" for e in eventos))
    llamadas, final = flujo.leer_traza(traza)
    progs = flujo.programas(llamadas)
    assert [(x["phase"], x["ok"], x["sello_error"]) for x in progs] == [
        ("check", True, None), ("add", False, "E103"), ("add", False, "E103"), ("add", True, None),
        ("check", False, None)]
    f = flujo.fricciones(llamadas, "inc")
    assert (f["e103"], f["e103_tras_check"], f["view"], f["sig"]) == (2, 1, 1, 1)
    assert flujo.aceptado_en(llamadas, "inc", IMPL) == 4
    assert flujo.aceptado_en(llamadas, "aux", IMPL) is None
    assert flujo.uso(final)["fin"] == "error_max_turns"


def test_mutantes_lee_las_filas_del_flujo_sin_mutar_el_contrato(tmp_path):
    fila = {"problem": "inc", "cond": flujo.COND, "model": "haiku", "accepted_at": 2,
            "code": POS_V1 + INC, "contrato": {"fns": ["pos"]}}
    corrida = tmp_path / "flujo.jsonl"
    corrida.write_text(json.dumps(fila) + "\n")
    [sol] = mutantes.cargar([corrida], mutantes.COLUMNAS, None)
    assert sol["congelados"] == ("pos",)
    _, muts = mutantes.mutar(sol["cond"], sol["code"], sol["congelados"])
    assert muts and all(m["fn"] == "inc" for m in muts)
    assert "sello_mcp·haiku" in mutantes.resumen([{**sol, "recuento": mutantes.contar([])}], "hoy")
