"""Contratos sin cuerpo: `{ sorry }` guarda un contrato que espera implementación (2026-09-29).

El hash de un hueco es el hash de su contrato, y una implementación lo rellena si, con el cuerpo
cambiado por `sorry`, da ese mismo hash. El contrato es de quien lo escribe: solo su autor le
cambia el contrato a ese nombre (E103). Quien llama a un hueco se prueba con su contrato, sus
ejemplos que llegan al hueco quedan pendientes y el cierre lo lista. Decisión en el vault:
'Un contrato sin cuerpo es un hueco con dueño'.
"""

import sqlite3

import pytest

from sello.compile import check_source
from sello.errors import SelloError
from sello.hash import contract_hashes, hash_program, short
from sello.nodes import Hole
from sello.parser import parse
from sello.pretty import unparse_fn
from sello.prover import UNKNOWN, prove_program
from sello.store import Store

ES_PAR = """
fn es_par(n: Int) -> Bool
  requires 1 == 1
  ensures result == (n % 2 == 0)
  effects pure
  example es_par(4) == true
{ n % 2 == 0 }
"""

# El contrato lo escribe uno (sonnet) sin cuerpo; su helper `Bool` va completo.
DOBLE = """
fn doble(n: Int) -> Int
  requires n >= 0
  ensures result == n + n
  ensures es_par(result)
  effects pure
  example doble(3) == 6
{ sorry }
"""

HUECO = ES_PAR + DOBLE
IMPLEMENTADA = HUECO.replace("{ sorry }", "{ 2 * n }")
DEBIL = IMPLEMENTADA.replace("  ensures result == n + n\n", "")  # lo que hacía haiku tras un E201

CUADRUPLE = """
fn cuadruple(n: Int) -> Int
  requires n >= 0
  ensures result == 4 * n
  effects pure
  example cuadruple(1) == 4
{ doble(doble(n)) }
"""

# Falla con cualquier implementación que cumpla el contrato de doble, pero no hay cuerpo que
# ejecutar para confirmarlo.
MAL = """
fn mal(n: Int) -> Int
  requires n >= 0
  ensures result == 2 * n + 1
  effects pure
  example mal(0) == 1
{ doble(n) }
"""


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "store.db")


def by_name(out: list[dict]) -> dict[str, dict]:
    return {f["name"]: f for f in out}


# ---------- sintaxis ----------

def test_sorry_es_el_cuerpo_entero_y_el_texto_canonico_lo_conserva():
    doble = parse(HUECO).fns[1]
    assert isinstance(doble.body, Hole)
    assert unparse_fn(doble).endswith("{\n  sorry\n}")
    es_par = hash_program(parse(ES_PAR))["es_par"]
    assert hash_program(parse(unparse_fn(doble)), {"es_par": es_par})["doble"] == hash_program(parse(HUECO))["doble"]


@pytest.mark.parametrize("cuerpo", ["{ sorry + 1 }", "{ if n == 0 then sorry else 1 }"])
def test_sorry_no_es_una_expresion(cuerpo):
    with pytest.raises(SelloError) as ei:
        parse(DOBLE.replace("{ sorry }", cuerpo))
    assert ei.value.code == "E000"


def test_sorry_esta_reservado():
    with pytest.raises(SelloError) as ei:
        parse(ES_PAR.replace("es_par(n: Int)", "es_par(sorry: Int)"))
    assert ei.value.code == "E000"


# ---------- el hash del contrato ----------

def test_el_hash_del_hueco_es_el_del_contrato_de_su_implementacion():
    hueco = hash_program(parse(HUECO))["doble"]
    impl = parse(IMPLEMENTADA)
    assert contract_hashes(impl)["doble"] == hueco
    assert hash_program(impl)["doble"] != hueco  # el cuerpo cuenta en la identidad de la función
    renombrada = IMPLEMENTADA.replace("(n: Int)", "(m: Int)").replace("{ 2 * n }", "{ 2 * m }")
    renombrada = renombrada.replace("n + n", "m + m").replace("n >= 0", "m >= 0")
    renombrada = renombrada.replace("es_par(m: Int)", "es_par(n: Int)")
    assert contract_hashes(parse(renombrada))["doble"] == hueco  # los nombres son alias
    assert contract_hashes(parse(DEBIL))["doble"] != hueco
    otro_helper = IMPLEMENTADA.replace("{ n % 2 == 0 }", "{ n % 2 != 1 }")
    assert contract_hashes(parse(otro_helper))["doble"] != hueco  # lo que las cláusulas llaman es contrato


# ---------- el probador ----------

def test_el_probador_no_intenta_un_hueco():
    """`verify` prueba el programa entero del cierre, huecos incluidos: un hueco se queda sin
    probar por no tener cuerpo, sin traducirlo ni tumbar al hijo."""
    v = prove_program(parse(HUECO))["doble"]
    assert (v.status, v.reason) == (UNKNOWN, "no body: `sorry`")


# ---------- check ----------

def test_check_acepta_un_hueco_y_lo_marca():
    out = check_source(HUECO)
    doble = by_name(out["functions"])["doble"]
    assert out["ok"] and doble["hole"] is True and doble["level"] == 0 and doble["pending"] == 1
    assert "hole" not in by_name(out["functions"])["es_par"]


# ---------- el almacén ----------

def test_un_hueco_se_guarda_en_nivel_0_con_sus_ejemplos_pendientes(store):
    doble = by_name(store.add(HUECO, author="sonnet"))["doble"]
    assert doble["hole"] is True
    assert doble["certificate"]["level"] == 0 and doble["certificate"]["ok"] is True
    assert doble["certificate"]["examples"] == 0 and doble["certificate"]["pending"] == 1
    sig = store.sig("doble")
    assert sig["hole"] is True and sig["contract_author"] == "sonnet" and "body_author" not in sig
    assert store.verify("doble")["certificate"]["level"] == 0
    assert [n.get("hole", False) for n in store.names()] == [True, False]


def test_rellenar_el_hueco_mueve_el_nombre_y_dice_que_implementa(store):
    store.add(HUECO, author="sonnet")
    hueco = store.resolve("doble")
    doble = by_name(store.add(IMPLEMENTADA, author="haiku"))["doble"]
    assert doble["implements"] == short(hueco) and "hole" not in doble
    assert doble["certificate"]["level"] == 2 and doble["certificate"]["examples"] == 1
    assert "pending" not in doble["certificate"]
    assert store.resolve("doble") != hueco
    sig = store.sig("doble")
    assert (sig["contract_author"], sig["body_author"], sig["implements"]) == ("sonnet", "haiku", short(hueco))


def test_quien_no_escribio_el_contrato_no_puede_cambiarlo(store):
    store.add(HUECO, author="sonnet")
    hueco = store.resolve("doble")
    for src in (DEBIL, DEBIL.replace("{ 2 * n }", "{ sorry }")):  # con cuerpo o como otro hueco
        with pytest.raises(SelloError) as ei:
            store.add(src, author="haiku")
        assert ei.value.code == "E103" and ei.value.extra["author"] == "sonnet"
        assert "called_by" not in ei.value.extra  # es el contrato de este nombre, no un helper de otro
        assert store.resolve("doble") == hueco
    n = store.db.execute("SELECT count(*) FROM functions").fetchone()[0]
    assert n == 2  # nada de lo rechazado se guardó


def test_el_autor_del_contrato_si_puede_cambiarlo(store):
    store.add(HUECO, author="sonnet")
    doble = by_name(store.add(DEBIL.replace("{ 2 * n }", "{ sorry }"), author="sonnet"))["doble"]
    assert doble["hole"] is True and store.sig("doble")["ensures"] == ["es_par(result)"]


def test_la_guarda_sigue_al_contrato_despues_de_rellenarlo(store):
    store.add(HUECO, author="sonnet")
    store.add(IMPLEMENTADA, author="haiku")
    with pytest.raises(SelloError) as ei:
        store.add(DEBIL, author="haiku")
    assert ei.value.code == "E103"
    store.add(IMPLEMENTADA.replace("{ 2 * n }", "{ n + n }"), author="haiku")  # otro cuerpo, mismo contrato


def test_sin_autores_no_se_bloquea_nada(store):
    store.add(HUECO)
    assert "hole" not in by_name(store.add(DEBIL))["doble"]


# Otra versión del helper del contrato, con el mismo nombre: lo que guardó haiku.
OTRO_ES_PAR = ES_PAR.replace("{ n % 2 == 0 }", "{ n % 2 != 1 }")


def test_otro_autor_no_mueve_el_nombre_de_un_helper_del_contrato(store):
    """Regresión 2026-10-01 (flujo-2026-10-01-0027-control, second_largest). Quien rellenaba guardó,
    en un add aparte, sus propias versiones de los helpers del contrato con los mismos nombres, y
    movió sus alias. Desde ahí, el contrato copiado tal cual de `view` enlazaba esos nombres con las
    versiones nuevas, daba otro hash y salía E103 sin salida. Nota 'Un hueco se rellena por el MCP
    igual que en el banco'."""
    store.add(HUECO, author="sonnet")
    es_par, hueco = store.resolve("es_par"), store.resolve("doble")
    with pytest.raises(SelloError) as ei:
        store.add(OTRO_ES_PAR, author="haiku")
    assert ei.value.code == "E103" and ei.value.function == "es_par"
    assert (ei.value.extra["author"], ei.value.extra["contract"]) == ("sonnet", short(hueco))
    assert store.resolve("es_par") == es_par
    # El texto que enseña view, con un cuerpo, sigue rellenando el hueco.
    fuente = store.view("doble")["source"].replace("sorry", "2 * n")
    assert by_name(store.add(fuente, author="haiku"))["doble"]["implements"] == short(hueco)
    with pytest.raises(SelloError) as ei:  # y la guarda sigue al contrato después de rellenarlo
        store.add(OTRO_ES_PAR, author="haiku")
    assert ei.value.code == "E103"


def test_la_guarda_del_helper_alcanza_a_los_helpers_de_sus_helpers(store):
    # Si quien rellena copia el texto de un helper del contrato, los nombres que ese texto llama
    # también tienen que seguir donde estaban.
    par_de = ES_PAR.replace("es_par", "par_de").replace("{ n % 2 == 0 }", "{ es_par(n) }")
    store.add(ES_PAR + par_de + DOBLE.replace("es_par(result)", "par_de(result)"), author="sonnet")
    with pytest.raises(SelloError) as ei:
        store.add(OTRO_ES_PAR, author="haiku")
    assert ei.value.code == "E103" and ei.value.function == "es_par"


def test_e103_senala_el_helper_cuando_el_fichero_lo_redefine(store):
    # El mismo fichero trae el contrato tal cual y otra versión del helper: el error apunta a la
    # causa, el helper, no a la principal.
    store.add(HUECO, author="sonnet")
    with pytest.raises(SelloError) as ei:
        store.add(OTRO_ES_PAR + DOBLE.replace("{ sorry }", "{ 2 * n }"), author="haiku")
    assert ei.value.code == "E103" and ei.value.function == "es_par"


def test_el_dueno_del_contrato_si_mueve_sus_helpers_y_sin_autores_nadie_bloquea(store, tmp_path):
    store.add(HUECO, author="sonnet")
    store.add(OTRO_ES_PAR, author="sonnet")
    assert store.resolve("es_par") == hash_program(parse(OTRO_ES_PAR))["es_par"]
    anonimo = Store(tmp_path / "anonimo.db")
    anonimo.add(HUECO)
    anonimo.add(OTRO_ES_PAR)


def test_rellenar_un_hueco_que_otro_contrato_llama_no_es_mover_un_helper(store):
    # Rellenar mueve el nombre del hueco a su implementación, aunque el contrato de otro hueco lo
    # llame en sus cláusulas: eso no cambia de contrato.
    cuadruple = CUADRUPLE.replace("ensures result == 4 * n", "ensures result == doble(doble(n))")
    store.add(HUECO + cuadruple.replace("{ doble(doble(n)) }", "{ sorry }"), author="sonnet")
    assert "implements" in by_name(store.add(IMPLEMENTADA, author="haiku"))["doble"]


def test_lo_que_ensena_sig_basta_para_reescribir_el_contrato(store):
    """Firma, cláusulas y ejemplos, en su orden. Sin los ejemplos, haiku inventaba los suyos y
    chocaba con E103 en todos los problemas (flujo-2026-10-01-0021-mcp)."""
    dos = HUECO.replace("  example doble(3) == 6\n", "  example doble(3) == 6\n  example doble(0) == 0\n")
    store.add(dos, author="sonnet")
    sig = store.sig("doble")
    texto = (f"fn {sig['signature']}\n" + "".join(f"  requires {r}\n" for r in sig["requires"])
             + "".join(f"  ensures {e}\n" for e in sig["ensures"]) + f"  effects {sig['effects']}\n"
             + "".join(f"  example {x}\n" for x in sig["examples"]) + "{ 2 * n }")
    assert "implements" in by_name(store.add(texto, author="haiku"))["doble"]


def test_quien_llama_a_un_hueco_se_prueba_con_su_contrato_y_espera_sus_ejemplos(store):
    store.add(HUECO, author="sonnet")
    hueco = {"name": "doble", "hash": short(store.resolve("doble")), "level": 0, "hole": True}
    c = by_name(store.add(CUADRUPLE))["cuadruple"]["certificate"]
    for cert in (c, store.sig("cuadruple")["certificate"], store.verify("cuadruple")["certificate"]):
        assert cert["level"] == 2 and cert["examples"] == 0 and cert["pending"] == 1
        assert cert["closure_level"] == 0 and cert["rests_on"] == [hueco]
    [f] = check_source(CUADRUPLE, store=store)["functions"]
    assert f["level"] == 2 and f["pending"] == 1


def test_un_contraejemplo_que_pasa_por_un_hueco_no_se_afirma(store):
    """Sin el cuerpo de doble no se puede ejecutar la entrada que da Z3: mal no se rechaza, se
    queda en nivel 0 con su ejemplo pendiente hasta que doble tenga cuerpo."""
    store.add(HUECO, author="sonnet")
    c = by_name(store.add(MAL))["mal"]["certificate"]
    assert c["level"] == 0 and c["ok"] is True and c["pending"] == 1


def test_eval_que_llega_a_un_hueco_es_E502(store):
    store.add(HUECO)
    with pytest.raises(SelloError) as ei:
        store.eval("doble(2)")
    assert ei.value.code == "E502"
    with pytest.raises(SelloError) as ei:
        store.eval("doble(-1)")
    assert ei.value.code == "E300"  # el requires del hueco se comprueba igual


def test_rellenar_el_hueco_dice_quien_sigue_llamandolo(store):
    store.add(HUECO, author="sonnet")
    store.add(CUADRUPLE)
    doble = by_name(store.add(IMPLEMENTADA, author="haiku"))["doble"]
    assert [u["name"] for u in doble["callers_on_hole"]] == ["cuadruple"]
    c = by_name(store.add(CUADRUPLE))["cuadruple"]["certificate"]  # añadida otra vez, enlaza el cuerpo
    assert c["level"] == 2 and c["examples"] == 1 and c["closure_level"] == 2


# ---------- almacenes de antes ----------

VIEJO = """
CREATE TABLE functions (
  hash TEXT PRIMARY KEY, name TEXT, source TEXT, signature TEXT, ret TEXT, effects TEXT,
  requires TEXT, ensures TEXT, deps TEXT, created_at TEXT);
CREATE TABLE names (name TEXT PRIMARY KEY, hash TEXT, updated_at TEXT);
CREATE TABLE certificates (
  hash TEXT PRIMARY KEY, level INTEGER, ok INTEGER, examples INTEGER, verified_at TEXT, error TEXT);
"""


def test_un_almacen_de_antes_se_abre_y_sigue_funcionando(tmp_path):
    db = sqlite3.connect(tmp_path / "store.db")
    db.executescript(VIEJO)
    db.close()
    store = Store(tmp_path / "store.db")
    assert by_name(store.add(HUECO))["doble"]["certificate"]["pending"] == 1
    assert by_name(store.add(IMPLEMENTADA))["doble"]["certificate"]["level"] == 2
