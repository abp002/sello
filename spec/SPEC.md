# Sello v0 (draft)

Sello is a small, pure, statically typed language. Every function carries a contract.
Code you write is stored by the hash of its syntax tree; names are aliases.

> Everything below is provisional and exists to be measured. Syntax will change.

## 1. Values and types

`Int` (arbitrary precision), `Bool`, `Text`, `List[T]`, `Option[T]`. Nothing else in v0.

## 2. Functions

A function is: a name, typed parameters, a return type, a contract, a body.

```
fn factorial(n: Int) -> Int
  requires n >= 0
  ensures result >= 1
  effects pure
  example factorial(0) == 1
  example factorial(5) == 120
  example factorial(3) == 6
{
  if n == 0 then 1 else n * factorial(n - 1)
}
```

Rules:

- `requires`, `ensures`, `effects` and at least one `example` are **mandatory**.
  Omitting any of them is error `E100`. `requires` and `ensures` may appear several
  times; all of them must hold. A clause that is just `true` is error `E102`.
- `result` names the return value inside `ensures`.
- `effects` is `pure` in v0. Other effects (`io`, `random`) are reserved.
- Examples are executed at compile time. A failing example is error `E200`.

## 3. Expressions

Literals (`42`, `true`, `"text"`, `[1, 2]`, `Some(3)`, `None`) · `if c then a else b` ·
Int arithmetic `+ - * / %` (`/` is integer division rounding down, like Python `//`) ·
`and` / `or` short-circuit: the right side is not evaluated when the left decides ·
`++` concatenates two `List` or two `Text` · comparison `== != < <= > >=` (`<` family on
Int only) · `and or not` · function call `f(x, y)` · `match` on `Option` and `List`:

```
match xs {
  [] => 0
  [h, ..t] => h + sum(t)
}
```

Patterns: `[]`, `[h, ..t]` (either part may be `_`), `None`, `Some(x)`, `_`, or a name
that binds the whole value. A match must cover every case (`E404`).

There is no `implies`, `|`, `&&`, `!`, `let` or `where`. Write `not a or b`, `or`, `and`,
`not`, and a helper function.

No loops. Recursion only. No mutation. No global state. No variables: name things by
making a function. `x / 0` is a runtime error (`E500`); rule it out with `requires`.

## 4. Contracts

- `requires` states everything the task lets you assume about the arguments (a value is
  unique, the list has no repeats, `k` is within bounds). Whatever is not in `requires`
  the body must handle. It is checked at every call, including calls made while running
  examples. A call whose arguments violate `requires` is error `E300`.
- `ensures` must reject wrong results: a clause that every return value satisfies
  certifies nothing. A bound alone (`result >= 1`, `result <= len(xs)`) does not reject
  a wrong value inside the bound. State what `result` contains or how it relates to the
  arguments: `contains(xs, result) and forall x in xs: x <= result`. When the words
  below cannot say it, write a `Bool` helper `fn` and call it: `ensures is_sorted_desc(result)`.
  It is checked on every return. A body that returns a value violating `ensures` is
  error `E201`. `result` names the return value.
- Both are checked by execution on every call (verification level 1). The compiler also
  tries to **prove** every `ensures` from `requires` and from the contracts of the functions
  the body calls, for all inputs (level 2, an SMT solver). When it finds an input that breaks
  a contract it reports the usual `E201`, `E300` or `E500` for that input, with
  `"found_by": "prover"` and the failing call in `"input"`. When it cannot decide, nothing is
  rejected: the function simply stays at level 1. A recursive function is proven only if some
  argument decreases at every recursive call.

Inside `requires` and `ensures` **only** (using them in a body or an example is `E401`):

| Form | Type | Meaning |
|---|---|---|
| `len(xs)` | `Int` | length of `xs` |
| `count(xs, x)` | `Int` | how many elements of `xs` equal `x` |
| `contains(xs, x)` | `Bool` | `count(xs, x) > 0` |
| `distinct(xs)` | `Bool` | no value appears twice in `xs` |
| `sorted(xs)` | `Bool` | `xs` is non-decreasing (`List[Int]` only) |
| `forall x in xs: P` | `Bool` | `P` holds for every element `x` of `xs` (true for `[]`) |
| `exists x in xs: P` | `Bool` | `P` holds for some element `x` of `xs` (false for `[]`) |

A quantifier may follow `and`, `or` or `not`; its body extends to the end of the clause
(or to the closing parenthesis). These names are reserved (`E402`).

```
fn drop(xs: List[Int], k: Int) -> List[Int]
  requires k >= 0 and k <= len(xs)
  ensures len(result) == len(xs) - k
  ensures forall x in result: contains(xs, x)
  effects pure
  example drop([1, 2, 3], 1) == [2, 3]
  example drop([1, 2, 3], 3) == []
{
  if k == 0 then xs else match xs {
    [] => []
    [_, ..t] => drop(t, k - 1)
  }
}
```

## 5. The store

The compiler does not compile files. `sello add FILE` parses, checks and hashes each
function, runs its examples, tries to prove its contract, and stores it with its contract
and its **certificate**: which verification level passed (2: proven for every input, given
what the functions it calls promise; 1: the examples passed), how many examples, when.
Names are aliases: renaming a function or a parameter does not change its hash. A function
whose hash already has a certificate is never re-verified. A caller's hash includes its
callees' hashes, so changing a dependency re-verifies only what uses it.

Reading is an API, not a file. Every command prints JSON:

| Command | Returns |
|---|---|
| `sello add FILE` | per function: name, hash, `cached`, certificate |
| `sello sig NAME` | signature + `requires` + `ensures` + `effects` + certificate, **no body** |
| `sello view NAME` | canonical source |
| `sello deps NAME` / `sello users NAME` | what it calls / what calls it |
| `sello names` | every name with its hash and signature |
| `sello verify NAME` | re-runs verification and refreshes the certificate |
| `sello eval EXPR` | evaluates an expression against the store |

## 6. Errors

All errors are JSON: `{"code", "where", "what", "fix", "example"}`. Codes are stable.

| Code | What | Fix |
|---|---|---|
| E000 | Syntax error | Follow the grammar above |
| E100 | Missing contract clause | Add `requires`, `ensures`, `effects` or an `example` |
| E101 | Unknown effect | Only `pure` exists in v0 |
| E102 | Trivial contract clause | `requires true` / `ensures true` certify nothing; state what you assume and what a wrong result would break |
| E200 | Example failed | Body or example is wrong; the message shows expected vs got |
| E201 | Postcondition violated | Body returned a value that breaks `ensures` |
| E300 | Precondition violated at a call | Guard the call with `if`, or strengthen the caller's `requires` |
| E400 | Type mismatch | Message shows expected and actual types |
| E401 | Unknown name | Only parameters, functions in this file, `result` in `ensures`, and the contract words above inside `requires`/`ensures` |
| E402 | Duplicate definition | One definition per name; `len`, `count`, `contains`, `distinct`, `sorted` are reserved |
| E403 | Wrong number of arguments | Match the signature |
| E404 | Non-exhaustive match | Cover `[]` and `[h, ..t]`, or `None` and `Some(x)`, or add `_ =>` |
| E500 | Runtime error | Division by zero or recursion too deep; add a `requires` |

## 7. Tooling

`sello check FILE` parses, typechecks, runs every example and proves what it can. Output
is JSON: `{"ok": true, "functions": [{"name", "signature", "examples", "level"}, ...],
"proven": N}` or `{"ok": false, "error": {...}}`. A function at level 1 also carries
`"unproven"`: why the prover could not decide. `sello mcp` serves the same API to agents
over MCP (stdio); its `sello_spec` tool returns this document.
