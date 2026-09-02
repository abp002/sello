from conftest import MAX, fails_with

from sello.compile import check_source


def test_falta_clausula_es_E100():
    e = fails_with("fn f(a: Int) -> Int\n  requires 1 == 1\n{ a }", "E100")
    assert "ensures" in e.detail and "example" in e.detail


def test_efecto_desconocido_es_E101():
    fails_with("fn f(a: Int) -> Int\n  requires 1 == 1\n  ensures 1 == 1\n  effects io\n  example f(1) == 1\n{ a }", "E101")


def test_tipo_incorrecto_es_E400_con_esperado_y_actual():
    e = fails_with("fn f(a: Int) -> Bool\n  requires 1 == 1\n  ensures 1 == 1\n  effects pure\n  example f(1)\n{ a + 1 }", "E400")
    assert e.extra == {"expected": "Bool", "actual": "Int"}


def test_nombre_desconocido_es_E401_y_result_solo_en_ensures():
    e = fails_with("fn f(a: Int) -> Int\n  requires result > 0\n  ensures 1 == 1\n  effects pure\n  example f(1) == 1\n{ a }", "E401")
    assert "ensures" in e.detail


def test_aridad_es_E403():
    fails_with(MAX + "\nfn g(x: Int) -> Int\n  requires 1 == 1\n  ensures 1 == 1\n  effects pure\n  example g(1) == 1\n{ max(x) }", "E403")


def test_match_no_exhaustivo_es_E404():
    src = "fn f(xs: List[Int]) -> Int\n  requires 1 == 1\n  ensures 1 == 1\n  effects pure\n  example f([]) == 0\n{ match xs { [] => 0 } }"
    fails_with(src, "E404")


def test_lista_vacia_unifica_con_lista_de_int():
    src = "fn f(xs: List[Int]) -> List[Int]\n  requires 1 == 1\n  ensures 1 == 1\n  effects pure\n  example f([]) == []\n  example f([1]) == [1]\n{ if xs == [] then [] else xs }"
    assert check_source(src)["ok"]


def test_concatenacion_solo_entre_secuencias_del_mismo_tipo():
    fails_with("fn f(a: Int) -> Int\n  requires 1 == 1\n  ensures 1 == 1\n  effects pure\n  example f(1) == 1\n{ a ++ 1 }", "E400")
    ok = "fn f(xs: List[Int]) -> List[Int]\n  requires 1 == 1\n  ensures 1 == 1\n  effects pure\n  example f([1]) == [1, 0]\n{ xs ++ [0] }"
    assert check_source(ok)["ok"]


CABECERA = "fn f(xs: List[Int]) -> Int\n  requires 1 == 1\n  ensures 1 == 1\n  effects pure\n  example f([]) == 0\n"


def test_vocabulario_de_listas_solo_en_contratos_es_E401():
    e = fails_with(CABECERA + "{ len(xs) }", "E401")
    assert "requires" in e.detail and "ensures" in e.detail
    fails_with(CABECERA + "{ if forall x in xs: x > 0 then 1 else 0 }", "E401")


def test_nombres_del_vocabulario_reservados_es_E402():
    fails_with("fn len(xs: List[Int]) -> Int\n  requires 1 == 1\n  ensures 1 == 1\n  effects pure\n  example len([]) == 0\n{ 0 }", "E402")


def test_vocabulario_tipa_sobre_el_elemento_de_la_lista():
    e = fails_with(CABECERA.replace("requires 1 == 1", 'requires count(xs, "a") == 0') + "{ 0 }", "E400")
    assert e.extra == {"expected": "Int", "actual": "Text"}
    fails_with(CABECERA.replace("requires 1 == 1", "requires len(3) == 0") + "{ 0 }", "E400")
    fails_with(CABECERA.replace("requires 1 == 1", "requires len(xs, xs) == 0") + "{ 0 }", "E403")
    fails_with(CABECERA.replace("requires 1 == 1", "requires forall x in xs: x") + "{ 0 }", "E400")
    ok = CABECERA.replace("ensures 1 == 1", "ensures forall x in xs: result >= x or contains(xs, result)")
    assert check_source(ok + "{ 0 }")["ok"]


def test_sorted_solo_sobre_listas_de_int():
    src = "fn f(ts: List[Text]) -> Int\n  requires sorted(ts)\n  ensures 1 == 1\n  effects pure\n  example f([]) == 0\n{ 0 }"
    fails_with(src, "E400")
