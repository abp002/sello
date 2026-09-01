# Sello v0 (draft)

Sello is a small, pure, statically typed language. Every function carries a contract.
Code you write is stored by the hash of its syntax tree; names are aliases.

> Everything below is provisional and exists to be measured. Syntax will change.

## 1. Values and types

`Int` (arbitrary precision), `Bool`, `Text`, `List[T]`, `Option[T]`. Nothing else in v0.

## 2. Functions

A function is: a name, typed parameters, a return type, a contract, a body.

```
fn max(a: Int, b: Int) -> Int
  requires true
  ensures result >= a and result >= b
  effects pure
  example max(1, 2) == 2
  example max(5, 5) == 5
  example max(-3, -7) == -3
{
  if a >= b then a else b
}
```

Rules:

- `requires`, `ensures`, `effects` and at least one `example` are **mandatory**.
  Omitting any of them is error `E100`. `requires` and `ensures` may appear several
  times; all of them must hold.
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

Patterns: `[]`, `[h, ..t]`, `None`, `Some(x)`, `_`, or a name that binds the whole
value. A match must cover every case (`E404`).

No loops. Recursion only. No mutation. No global state. No variables: name things by
making a function. `x / 0` is a runtime error (`E500`); rule it out with `requires`.

## 4. Contracts

- `requires` is checked at every call, including calls made while running examples.
  A call whose arguments violate `requires` is error `E300`.
- `ensures` is checked on every return. A body that returns a value violating `ensures`
  is error `E201`. `result` names the return value.
- In v0 both are checked by execution (verification level 1). Later levels: SMT solver
  (level 2), runtime guard (level 3).

## 5. The store

The compiler does not compile files. It parses, normalizes and hashes each function, then
stores it with its contract and its **certificate**: which contracts were verified, at
which level, and when. A function whose hash is already certified is never re-verified.

Reading is an API, not a file:

| Query | Returns |
|---|---|
| `sig <name>` | signature + contract + certificate, no body |
| `deps <name>` | hashes this function calls |
| `users <name>` | hashes that call this function |
| `verify <name>` | runs verification, updates the certificate |

## 6. Errors

All errors are JSON: `{"code", "where", "what", "fix", "example"}`. Codes are stable.

| Code | What | Fix |
|---|---|---|
| E000 | Syntax error | Follow the grammar above |
| E100 | Missing contract clause | Add `requires`, `ensures`, `effects` or an `example` |
| E101 | Unknown effect | Only `pure` exists in v0 |
| E200 | Example failed | Body or example is wrong; the message shows expected vs got |
| E201 | Postcondition violated | Body returned a value that breaks `ensures` |
| E300 | Precondition violated at a call | Guard the call with `if`, or strengthen the caller's `requires` |
| E400 | Type mismatch | Message shows expected and actual types |
| E401 | Unknown name | Only parameters, functions in this file, and `result` in `ensures` |
| E402 | Duplicate definition | One definition per name |
| E403 | Wrong number of arguments | Match the signature |
| E404 | Non-exhaustive match | Cover `[]` and `[h, ..t]`, or `None` and `Some(x)`, or add `_ =>` |
| E500 | Runtime error | Division by zero or recursion too deep; add a `requires` |

## 7. Tooling

`sello check FILE` parses, typechecks and runs every example. Output is JSON:
`{"ok": true, ...}` or `{"ok": false, "error": {...}}`.
