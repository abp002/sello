"""Lexer: texto -> tokens. Un bucle sobre caracteres."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import SelloError

KEYWORDS = {
    "fn", "requires", "ensures", "effects", "example",
    "if", "then", "else", "match",
    "true", "false", "None", "Some",
    "and", "or", "not",
}
SYMBOLS2 = {"->", "=>", "==", "!=", "<=", ">=", "..", "++"}
SYMBOLS1 = set("()[]{},:+-*/%<>_")


@dataclass(frozen=True)
class Token:
    kind: str  # INT TEXT NAME KW SYM EOF
    value: str
    line: int
    col: int


def lex(src: str) -> list[Token]:
    out: list[Token] = []
    i, line, col = 0, 1, 1
    n = len(src)

    def emit(kind: str, value: str, l: int, c: int) -> None:
        out.append(Token(kind, value, l, c))

    while i < n:
        ch = src[i]
        if ch == "\n":
            i += 1; line += 1; col = 1
            continue
        if ch in " \t\r":
            i += 1; col += 1
            continue
        if ch == "#":
            while i < n and src[i] != "\n":
                i += 1
            continue
        start_col = col
        if ch.isdigit():
            j = i
            while j < n and src[j].isdigit():
                j += 1
            emit("INT", src[i:j], line, start_col)
            col += j - i; i = j
            continue
        if ch.isalpha():
            j = i
            while j < n and (src[j].isalnum() or src[j] == "_"):
                j += 1
            word = src[i:j]
            emit("KW" if word in KEYWORDS else "NAME", word, line, start_col)
            col += j - i; i = j
            continue
        if ch == '"':
            j = i + 1
            buf = []
            while j < n and src[j] != '"':
                if src[j] == "\n":
                    raise SelloError("E000", "unterminated text literal", line, start_col)
                if src[j] == "\\" and j + 1 < n:
                    esc = src[j + 1]
                    buf.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(esc, esc))
                    j += 2
                    continue
                buf.append(src[j]); j += 1
            if j >= n:
                raise SelloError("E000", "unterminated text literal", line, start_col)
            emit("TEXT", "".join(buf), line, start_col)
            col += j + 1 - i; i = j + 1
            continue
        two = src[i:i + 2]
        if two in SYMBOLS2:
            emit("SYM", two, line, start_col)
            i += 2; col += 2
            continue
        if ch in SYMBOLS1:
            emit("SYM", ch, line, start_col)
            i += 1; col += 1
            continue
        raise SelloError("E000", f"unexpected character {ch!r}", line, start_col)
    emit("EOF", "", line, col)
    return out
