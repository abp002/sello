"""El instrumento de '¿el nivel 2 depende de los nombres?': renombrar sin cambiar el programa y
clasificar las diferencias.

Si `renombrar` tocara una variable que se llama como una función, o dejara una llamada sin
reescribir, compararía otro programa y la diferencia saldría «por nombres». Si `H` no diera los
nombres del almacén, no mediría lo que ve el almacén. Si `comparar` contara el reloj o el ruido
como nombres, inventaría el efecto.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench"))
import nombres  # noqa: E402

from sello.hash import hash_program  # noqa: E402
from sello.parser import parse  # noqa: E402
from sello.store import Store  # noqa: E402

PROG = """
fn total(xs: List[Int]) -> Int
  requires len(xs) >= 0
  ensures result == suma(xs)
  effects pure
  example total([1, 2]) == 3
{
  suma(xs)
}

fn suma(xs: List[Int]) -> Int
  requires len(xs) >= 0
  ensures len(xs) > 0 or result == 0
  effects pure
  example suma([]) == 0
{
  match xs {
    [] => 0
    [h, ..t] => h + suma(t)
  }
}

fn usa(suma: Int) -> Int
  requires suma >= 0
  ensures result == suma + 1
  effects pure
  example usa(1) == 2
{
  suma + 1
}
"""


def test_renombrar_conserva_los_hashes_y_deja_las_variables():
    for esquema in nombres.ESQUEMAS:
        nuevo, vuelta = nombres.variante(PROG, esquema)
        assert set(vuelta.values()) == {"total", "suma", "usa"}
        assert {vuelta[n]: h for n, h in hash_program(parse(nuevo)).items()} == hash_program(parse(PROG))
    nuevo, vuelta = nombres.variante(PROG, "H")
    usa = next(f for f in parse(nuevo).fns if vuelta[f.name] == "usa")
    assert [p.name for p in usa.params] == ["suma"]  # la variable no es una llamada
    assert "suma(" not in nuevo and "total(" not in nuevo


def test_h_da_los_nombres_del_almacen(tmp_path):
    st = Store(tmp_path / "s.db")
    st.add(PROG)
    prog, alias = st.program_of_names()
    _, vuelta = nombres.variante(PROG, "H")
    assert {vuelta[a] for a in alias.values()} == set(alias)
    assert {f.name for f in prog.fns} == set(vuelta)


def test_dos_funciones_iguales_no_se_comparan_en_h():
    dup = PROG + ("fn usa(" + PROG.split("fn usa(")[1]).replace("usa(", "usa2(")  # misma función, otro nombre
    assert nombres.variante(dup, "H") is None
    assert nombres.variante(dup, "O") is not None


def _fila(pid, esquema, rep, level, unproven=""):
    return {"id": pid, "esquema": esquema, "rep": rep,
            "veredicto": {"ok": True, "funciones": {"f": {"level": level, "unproven": unproven}}}}


def test_comparar_separa_nombres_reloj_y_ruido():
    rows = []
    for e in nombres.ESQUEMAS:
        for rep in (1, 2):
            rows.append(_fila("igual", e, rep, 2))
            rows.append(_fila("nombres", e, rep, 1 if e == "H" else 2, "undecided" if e == "H" else ""))
            reloj = e == "X" and rep == 2
            rows.append(_fila("reloj", e, rep, 1 if reloj else 2, "timeout (wall clock)" if reloj else ""))
            ruido = e == "O" and rep == 1
            rows.append(_fila("ruido", e, rep, 1 if ruido else 2, "undecided" if ruido else ""))
    rows.append({"id": "roto", "esquema": "H", "rep": 1, "veredicto": None})
    c = nombres.comparar(rows)
    assert [f["id"] for f in c["por_nombres"]] == ["nombres"]
    assert [f["id"] for f in c["por_reloj"]] == ["reloj"]
    assert [f["id"] for f in c["inestables"]] == ["ruido"]
    assert c["descartados"] == ["roto"]


def test_un_renombrado_que_cambia_el_programa_se_descarta(monkeypatch):
    bueno = nombres.renombrar
    monkeypatch.setattr(nombres, "renombrar", lambda code, mapa: bueno(code, mapa).replace("suma + 1\n}", "suma + 2\n}"))
    assert nombres.variante(PROG, "X") is None
