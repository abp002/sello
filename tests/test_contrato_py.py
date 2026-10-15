"""El contrato escrito por otro en Python (SEL-16): se extrae, se congela, se comprueba al ejecutar
y CrossHair lo busca romper. Es el brazo contra el que se compara Sello en el experimento decisivo."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench"))
import contrato_py as cp  # noqa: E402
import harness3 as h3  # noqa: E402

CONTRATO = '''
def is_asc(xs: list[int]) -> bool:
    return all(xs[i] < xs[i + 1] for i in range(len(xs) - 1))


def same_elems(xs: list[int], ys: list[int]) -> bool:
    return sorted(xs) == sorted(ys)


def helper_del_cuerpo(xs: list[int]) -> list[int]:
    return xs


def sort_distinct(xs: list[int]) -> list[int]:
    """
    pre: len(set(xs)) == len(xs)
    post: is_asc(__return__)
    post: same_elems(xs, __return__)
    """
    return helper_del_cuerpo(sorted(xs))
'''


def test_condiciones():
    assert cp.condiciones("x\n  pre: a > 0\npost: __return__ >= a\n post : b") == (["a > 0"], ["__return__ >= a", "b"])


def test_extraer_congela_la_cabecera_y_los_helpers_de_las_condiciones():
    c = cp.extraer(CONTRATO, "sort_distinct")
    assert c.nombres == ["is_asc", "same_elems"]  # helper_del_cuerpo es del cuerpo, no del contrato
    assert "return helper_del_cuerpo" not in c.texto and "..." in c.texto
    assert "post: same_elems(xs, __return__)" in c.texto


def test_el_cuerpo_puede_cambiar_y_el_contrato_no():
    c = cp.extraer(CONTRATO, "sort_distinct")
    assert cp.violacion(c, CONTRATO) is None
    otro_cuerpo = CONTRATO.replace("return helper_del_cuerpo(sorted(xs))", "return sorted(xs)")
    assert cp.violacion(c, otro_cuerpo) is None
    reformateado = CONTRATO.replace('    """\n    pre:', '    """\n        pre:')
    assert cp.violacion(c, reformateado) is None  # la sangría del docstring no cuenta
    assert "docstring" in cp.violacion(c, CONTRATO.replace("post: is_asc(__return__)\n", ""))
    assert "is_asc" in cp.violacion(c, CONTRATO.replace("xs[i] < xs[i + 1]", "xs[i] <= xs[i + 1]"))
    assert "signature" in cp.violacion(c, CONTRATO.replace("def sort_distinct(xs: list[int])", "def sort_distinct(ys: list[int])"))


P = {"fn": "sort_distinct", "python": "def sort_distinct(xs: list[int]) -> list[int]", "option": False}


def caso(args, expect):
    return {"args": args, "expect": expect, "zone": "domain"}


def test_al_ejecutar_un_post_violado_es_cazado_y_un_pre_violado_es_rechazo():
    malo = CONTRATO.replace("return helper_del_cuerpo(sorted(xs))", "return sorted(xs)[:1]")
    r = h3.ejecutar_python(malo, P, [caso([[3, 1, 2]], [1, 2, 3]), caso([[2, 2]], [2, 2])], contratos=True)
    assert [x["result"] for x in r] == ["caught", "reject"]
    # sin contratos activos, el mismo resultado incorrecto pasa en silencio
    r = h3.ejecutar_python(malo, P, [caso([[3, 1, 2]], [1, 2, 3])])
    assert [x["result"] for x in r] == ["wrong"]


def test_las_llamadas_recursivas_tambien_comprueban_el_contrato():
    src = '''
def down(n: int) -> int:
    """
    pre: n >= 0
    post: __return__ == 0
    """
    return 0 if n == 0 else down(n - 2)
'''
    r = h3.ejecutar_python(src, {"fn": "down", "option": False}, [caso([3], 0)], contratos=True)
    assert r[0]["result"] == "reject"  # down(1) llama a down(-1)


def test_crosshair_encuentra_el_contraejemplo_y_calla_si_no_lo_hay():
    malo = CONTRATO.replace("return helper_del_cuerpo(sorted(xs))", "return xs")
    assert cp.crosshair(malo).startswith("crosshair: false when calling sort_distinct(")
    assert cp.crosshair(CONTRATO) is None


def test_si_crosshair_no_puede_analizar_falla_en_alto():
    with pytest.raises(RuntimeError):
        cp.crosshair("def f(:\n")


def test_una_condicion_con_generador_ve_los_argumentos():
    # Regresión del humo de SEL-9: con eval(c, ns, env), un generador dentro de la condición no
    # veía los argumentos (NameError) y el contrato correcto de binary_search salía rechazado.
    src = '''
def first(xs: list[int]) -> int:
    """
    pre: all(xs[i] < xs[i + 1] for i in range(len(xs) - 1))
    post: all(__return__ <= v for v in xs)
    """
    return xs[0]
'''
    r = h3.ejecutar_python(src, {"fn": "first", "option": False}, [caso([[1, 2, 3]], 1)], contratos=True)
    assert r[0]["result"] == "ok", r[0]["detail"]


# ---------- unicidad del contrato en Python (issue #3): el nivel 3 con CrossHair ----------

COTA = '''
def count_greater(xs: list[int], t: int) -> int:
    """
    pre: len(xs) <= 4
    post: __return__ >= 0
    post: __return__ <= len(xs)
    """
    ...
'''

CONTENIDO = '''
def greater(xs: list[int], t: int) -> list[int]:
    return [x for x in xs if x > t]


def count_greater(xs: list[int], t: int) -> int:
    """
    pre: len(xs) <= 4
    post: __return__ == len(greater(xs, t))
    """
    ...
'''


def test_un_contrato_de_cotas_es_ambiguo_y_el_testigo_se_confirma():
    w = cp.ambiguo(COTA, "count_greater")
    assert w is not None
    args, r1, r2 = w
    assert r1 != r2 and len(args) == 2
    assert 0 <= r1 <= len(args[0]) and 0 <= r2 <= len(args[0])


def test_un_contrato_que_fija_la_respuesta_no_da_testigo():
    assert cp.ambiguo(CONTENIDO, "count_greater") is None


def test_un_testigo_que_no_cumple_el_contrato_no_se_da_por_bueno():
    assert cp.confirma_ambiguo(COTA, "count_greater", [[1], 0], 0, 1)
    assert not cp.confirma_ambiguo(COTA, "count_greater", [[1], 0], 0, 2)   # 2 > len(xs)
    assert not cp.confirma_ambiguo(COTA, "count_greater", [[1], 0], 1, 1)   # no son distintos
    assert not cp.confirma_ambiguo(COTA, "count_greater", [[1, 2, 3, 4, 5], 0], 0, 1)  # fuera del pre
