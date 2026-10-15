"""El oráculo del banco juzga cada caso con su propio tope, en Sello igual que en Python (issue #2):
un caso lento es un rechazo y no se lleva por delante a los demás."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench"))
import harness3 as h3  # noqa: E402
import juez  # noqa: E402

LENTA = """
fn slow(n: Int) -> Int
  requires (n >= 0)
  ensures (result >= 0)
  effects pure
  example (slow(0) == 0)
  example (slow(3) == 2)
{
  if (n < 2) then n else (slow((n - 1)) + slow((n - 2)))
}
"""


def test_un_caso_lento_no_tumba_a_los_demas():
    p = {"fn": "slow", "option": False}
    casos = [{"args": [0], "expect": 0, "zone": "domain"},
             {"args": [40], "expect": 102334155, "zone": "domain"}]
    r = h3.ejecutar_sello(LENTA, p, casos, timeout=30, prover=False)
    assert isinstance(r, list), r
    assert [c["result"] for c in r] == [juez.OK, juez.REJECT]
