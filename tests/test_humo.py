"""Test de humo: el paquete importa y declara versión."""

import sello


def test_importa_y_tiene_version():
    assert sello.__version__
