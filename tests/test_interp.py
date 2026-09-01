from conftest import fails_with

from sello.compile import check_source

REVERSE = """
fn reverse(xs: List[Int]) -> List[Int]
  requires true
  ensures true
  effects pure
  example reverse([]) == []
  example reverse([1, 2, 3]) == [3, 2, 1]
{
  match xs {
    [] => []
    [h, ..t] => reverse(t) ++ [h]
  }
}
"""

OPTION = """
fn head(xs: List[Text]) -> Option[Text]
  requires true
  ensures true
  effects pure
  example head([]) == None
  example head(["a", "b"]) == Some("a")
{ match xs { [] => None  [h, ..t] => Some(h) } }

fn head_or(xs: List[Text], d: Text) -> Text
  requires true
  ensures true
  effects pure
  example head_or([], "z") == "z"
  example head_or(["a"], "z") == "a"
{ match head(xs) { None => d  Some(x) => x } }
"""


def test_recursion_sobre_listas_y_concatenacion():
    assert check_source(REVERSE)["examples"] == 2


def test_option_y_texto():
    assert check_source(OPTION)["examples"] == 4


def test_division_entera_redondea_hacia_abajo():
    src = "fn f(a: Int) -> Int\n  requires true\n  ensures true\n  effects pure\n  example f(-7) == -4\n  example f(7) == 3\n{ a / 2 }"
    assert check_source(src)["ok"]


def test_division_por_cero_es_E500():
    e = fails_with("fn f(a: Int) -> Int\n  requires true\n  ensures true\n  effects pure\n  example f(1) == 1\n{ a / 0 }", "E500")
    assert "division by zero" in e.detail


def test_recursion_profunda_es_E500_no_crash():
    src = "fn f(n: Int) -> Int\n  requires true\n  ensures true\n  effects pure\n  example f(1) == 1\n{ f(n + 1) }"
    e = fails_with(src, "E500")
    assert "recursion" in e.detail
