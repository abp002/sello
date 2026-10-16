"""El oráculo del banco juzga cada caso con su propio tope, en Sello igual que en Python (issue #2):
un caso lento es un rechazo y no se lleva por delante a los demás."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench"))
import harness3 as h3  # noqa: E402
import juez  # noqa: E402

# Lenta aunque las llamadas se memoicen (issue #4): el contrato recorre n² enteros.
LENTA = """
fn slow(n: Int) -> Int
  requires (n >= 0)
  ensures forall i in 0..(n * n): i >= 0
  effects pure
  example (slow(0) == 0)
  example (slow(3) == 3)
{
  n
}
"""


def test_un_caso_lento_no_tumba_a_los_demas():
    p = {"fn": "slow", "option": False}
    casos = [{"args": [0], "expect": 0, "zone": "domain"},
             {"args": [100000], "expect": 100000, "zone": "domain"}]
    r = h3.ejecutar_sello(LENTA, p, casos, timeout=30, prover=False)
    assert isinstance(r, list), r
    assert [c["result"] for c in r] == [juez.OK, juez.REJECT]
