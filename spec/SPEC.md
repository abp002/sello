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
  Omitting any of them is error `E100`.
- `result` names the return value inside `ensures`.
- `effects` is `pure` in v0. Other effects (`io`, `random`) are reserved.
- Examples are executed at compile time. A failing example is error `E200`.

## 3. Expressions

Literals · `if c then a else b` · arithmetic `+ - * / %` · comparison `== != < <= > >=` ·
`and or not` · function call `f(x, y)` · `match` on `Option` and `List`:

```
match xs {
  [] => 0
  [h, ..t] => h + sum(t)
}
```

No loops. Recursion only. No mutation. No global state.

## 4. Contracts

- `requires` is checked at every call site. Calling with arguments the compiler cannot
  prove satisfy `requires` is error `E300`.
- `ensures` is checked against the body. In v0 it is checked by running the examples
  (verification level 1). Later levels: SMT solver (level 2), runtime guard (level 3).

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
| E100 | Missing contract clause | Add `requires`, `ensures`, `effects` or an `example` |
| E200 | Example failed | Body or example is wrong; the message shows expected vs got |
| E300 | Precondition not satisfied at call site | Guard the call or strengthen the caller's `requires` |
| E400 | Type mismatch | Message shows expected and actual types |
