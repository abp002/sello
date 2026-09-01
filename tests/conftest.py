import pytest

from sello.compile import check_source, compile_source, run_examples
from sello.errors import SelloError

MAX = """
fn max(a: Int, b: Int) -> Int
  requires true
  ensures result >= a and result >= b
  effects pure
  example max(1, 2) == 2
{
  if a >= b then a else b
}
"""


def fails_with(src: str, code: str) -> SelloError:
    """Comprueba que compilar+ejemplos falla con el código dado y devuelve el error."""
    with pytest.raises(SelloError) as ei:
        check_source(src)
    assert ei.value.code == code, f"esperaba {code}, salió {ei.value.code}: {ei.value.detail}"
    return ei.value
