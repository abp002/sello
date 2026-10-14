"""Con SELLO_DETERMINISTA, el hijo del probador corre sin ASLR y con la semilla de Python fija (SEL-5)."""

import pytest

from sello import prover


def test_sin_la_variable_el_hijo_arranca_como_siempre(monkeypatch):
    monkeypatch.delenv("SELLO_DETERMINISTA", raising=False)
    cmd, env = prover._child_cmd(["--only", "f"])
    assert cmd[0] == prover.sys.executable and env is None


def test_en_linux_el_hijo_va_sin_aslr_con_semilla_y_entorno_fijos(monkeypatch):
    monkeypatch.setenv("SELLO_DETERMINISTA", "1")
    monkeypatch.setenv("SELLO_TRAZA", "/tmp/t.jsonl")
    monkeypatch.setenv("RUIDO", "x" * 100)
    monkeypatch.setattr(prover.sys, "platform", "linux")
    cmd, env = prover._child_cmd(["--only", "f"])
    assert cmd[0].endswith("setarch") and cmd[1:3] == [prover.platform.machine(), "-R"]
    assert env["PYTHONHASHSEED"] == "0"
    assert env["SELLO_TRAZA"] == "/tmp/t.jsonl"  # los experimentos SELLO_* siguen llegando
    assert "RUIDO" not in env  # el entorno cambia la disposición de la memoria


def test_donde_no_se_puede_apagar_aslr_falla_en_vez_de_medir_con_azar(monkeypatch):
    monkeypatch.setenv("SELLO_DETERMINISTA", "1")
    monkeypatch.setattr(prover.sys, "platform", "darwin")
    with pytest.raises(RuntimeError, match="ASLR"):
        prover._child_cmd(["--only", "f"])


def test_los_milisegundos_van_con_ancho_fijo():
    # el reloj que queda cambia en cada ejecución: con otra longitud, otra memoria en el hijo
    assert prover._ms(5) == "000000005" and int(prover._ms(59_999)) == 59_999
    assert len(prover._ms(5)) == len(prover._ms(59_999))
