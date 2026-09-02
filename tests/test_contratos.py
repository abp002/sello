"""Los contratos son la regla de negocio de Sello: se testean en detalle."""

from conftest import fails_with

from sello.compile import check_source

FACT = """
fn factorial(n: Int) -> Int
  requires n >= 0
  ensures result >= 1
  effects pure
  example factorial(0) == 1
  example factorial(5) == 120
{ if n == 0 then 1 else n * factorial(n - 1) }
"""


def test_ejemplo_que_falla_es_E200_con_esperado_y_obtenido():
    src = FACT.replace("factorial(5) == 120", "factorial(5) == 121")
    e = fails_with(src, "E200")
    assert e.extra == {"expected": "121", "got": "120"}
    assert e.function == "factorial"


def test_precondicion_violada_desde_ejemplo_es_E300():
    src = FACT.replace("example factorial(0) == 1", "example factorial(-1) == 1")
    e = fails_with(src, "E300")
    assert e.extra["call"] == "factorial(-1)"


def test_precondicion_violada_desde_otra_funcion_señala_al_llamador():
    src = FACT + """
fn bad(n: Int) -> Int
  requires 1 == 1
  ensures 1 == 1
  effects pure
  example bad(3) == 2
{ factorial(n - 5) }
"""
    e = fails_with(src, "E300")
    assert e.function == "bad"


def test_postcondicion_violada_es_E201():
    src = FACT.replace("ensures result >= 1", "ensures result > 200")
    e = fails_with(src, "E201")
    assert e.extra["got"] == "1"


def test_todo_correcto_devuelve_resumen_con_firmas():
    r = check_source(FACT)
    assert r == {"ok": True, "examples": 2,
                 "functions": [{"name": "factorial", "signature": "factorial(n: Int) -> Int", "examples": 2}]}


CLAMP_DOBLE = """
fn clamp(x: Int, lo: Int, hi: Int) -> Int
  requires lo <= hi
  ensures result >= lo
  ensures result <= hi
  effects pure
  example clamp(5, 1, 10) == 5
  example clamp(-5, 1, 10) == 1
{ if x < lo then lo else if x > hi then hi else x }
"""


def test_varias_clausulas_ensures_son_conjuncion():
    """Hallazgo de la medición 2026-09-02: el modelo escribe dos `ensures` como en Dafny."""
    assert check_source(CLAMP_DOBLE)["ok"]
    roto = CLAMP_DOBLE.replace("ensures result <= hi", "ensures result <= 4")
    e = fails_with(roto, "E201")
    assert "result <= 4" in e.detail


# ---- vocabulario de listas (decisión 2026-09-02) ----

PRIMERO = """
fn primero(xs: List[Int]) -> Option[Int]
  requires 1 == 1
  ensures match result { None => xs == []  Some(m) => forall x in xs: x == m or count(xs, x) < count(xs, m) }
  effects pure
  example primero([]) == None
  example primero([2, 2, 3]) == Some(2)
{
  match xs {
    [] => None
    [h, ..t] => Some(h)
  }
}
"""


def test_forall_en_ensures_caza_el_empate_con_E201():
    """El caso `most_frequent`: el juez débil acepta, el contrato caza el empate."""
    assert check_source(PRIMERO)["ok"]
    e = fails_with(PRIMERO.replace("example primero([2, 2, 3]) == Some(2)", "example primero([2, 3]) == Some(2)"), "E201")
    assert e.extra["got"] == "Some(2)" and "forall" in e.detail


def test_distinct_en_requires_rechaza_repetidos_con_E300():
    src = PRIMERO.replace("requires 1 == 1", "requires distinct(xs)").replace("[2, 2, 3]", "[2, 3, 3]")
    e = fails_with(src, "E300")
    assert e.extra["call"] == "primero([2, 3, 3])"


def test_len_y_sorted_en_ensures():
    src = """
fn ordena2(a: Int, b: Int) -> List[Int]
  requires 1 == 1
  ensures len(result) == 2
  ensures sorted(result)
  effects pure
  example ordena2(3, 1) == [1, 3]
{ if a <= b then [a, b] else [b, a] }
"""
    assert check_source(src)["ok"]
    e = fails_with(src.replace("[b, a]", "[a, b]"), "E201")
    assert "sorted" in e.detail


def test_exists_sobre_lista_vacia_es_falso():
    src = """
fn algun_positivo(xs: List[Int]) -> Bool
  requires exists x in xs: x > 0
  ensures result
  effects pure
  example algun_positivo([0, 1]) == true
{ true }
"""
    assert check_source(src)["ok"]
    fails_with(src.replace("([0, 1])", "([])"), "E300")


def test_clausula_true_literal_es_E102():
    """Paso 2 de 'Un contrato trivial no certifica nada' (2026-09-02)."""
    e = fails_with(FACT.replace("requires n >= 0", "requires true"), "E102")
    assert "requires" in e.detail and e.function == "factorial"
    fails_with(FACT.replace("ensures result >= 1", "ensures true"), "E102")
