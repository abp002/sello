"""El almacén: funciones por hash, nombres como alias, certificados por hash.

Verificada una vez, verificada para siempre: un hash con certificado ok no se vuelve a
verificar. Como el hash de un llamador incluye el hash del llamado, cambiar una
dependencia invalida solo a quien la usa.
"""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
from pathlib import Path

from .checker import Checker, signature
from .compile import run_examples
from .errors import SelloError
from .hash import callees, hash_program, short
from .interp import Interpreter
from .nodes import Call, Expr, Fn, Program
from .parser import parse
from .pretty import unparse, unparse_fn

SCHEMA = """
CREATE TABLE IF NOT EXISTS functions (
  hash TEXT PRIMARY KEY, name TEXT, source TEXT, signature TEXT, ret TEXT, effects TEXT,
  requires TEXT, ensures TEXT, deps TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS names (name TEXT PRIMARY KEY, hash TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS certificates (
  hash TEXT PRIMARY KEY, level INTEGER, ok INTEGER, examples INTEGER, verified_at TEXT, error TEXT);
"""


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _rewrite_calls(e: Expr, mapping: dict[str, str]) -> None:
    from .nodes import children
    if isinstance(e, Call):
        e.name = mapping.get(e.name, e.name)
    for c in children(e):
        _rewrite_calls(c, mapping)


def _rewrite_fn(fn: Fn, mapping: dict[str, str]) -> None:
    for e in [*fn.requires, *fn.ensures, *fn.examples, fn.body]:
        _rewrite_calls(e, mapping)


class Store:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    # ---------- consultas ----------
    def resolve(self, name: str) -> str:
        row = self.db.execute("SELECT hash FROM names WHERE name = ?", (name,)).fetchone()
        if row is None:
            raise SelloError("E401", f"`{name}` is not in the store")
        return row["hash"]

    def function(self, h: str) -> sqlite3.Row:
        row = self.db.execute("SELECT * FROM functions WHERE hash = ?", (h,)).fetchone()
        if row is None:
            raise SelloError("E401", f"hash {short(h)} is not in the store")
        return row

    def certificate(self, h: str) -> dict | None:
        row = self.db.execute("SELECT * FROM certificates WHERE hash = ?", (h,)).fetchone()
        if row is None:
            return None
        d = {"level": row["level"], "ok": bool(row["ok"]), "examples": row["examples"],
             "verified_at": row["verified_at"]}
        if row["error"]:
            d["error"] = json.loads(row["error"])
        return d

    def names(self) -> list[dict]:
        rows = self.db.execute("SELECT n.name, n.hash, f.signature FROM names n JOIN functions f ON f.hash = n.hash ORDER BY n.name").fetchall()
        return [{"name": r["name"], "hash": short(r["hash"]), "signature": r["signature"]} for r in rows]

    def sig(self, name: str) -> dict:
        """Firma + contrato + certificado. Sin cuerpo: es lo que lee la IA."""
        h = self.resolve(name)
        f = self.function(h)
        return {"name": name, "hash": short(h), "signature": f["signature"],
                "requires": json.loads(f["requires"]), "ensures": json.loads(f["ensures"]),
                "effects": f["effects"], "certificate": self.certificate(h)}

    def view(self, name: str) -> dict:
        h = self.resolve(name)
        return {"name": name, "hash": short(h), "source": self.function(h)["source"]}

    def deps(self, name: str) -> list[dict]:
        h = self.resolve(name)
        d = json.loads(self.function(h)["deps"])
        return [{"name": n, "hash": short(dh)} for n, dh in sorted(d.items()) if dh != h]

    def users(self, name: str) -> list[dict]:
        h = self.resolve(name)
        out = []
        for r in self.db.execute("SELECT hash, name, deps FROM functions").fetchall():
            if r["hash"] != h and h in json.loads(r["deps"]).values():
                out.append({"name": r["name"], "hash": short(r["hash"])})
        return sorted(out, key=lambda x: x["name"])

    # ---------- carga de programas desde el almacén ----------
    def load_closure(self, roots: list[str]) -> tuple[Program, dict[str, str]]:
        """Programa con el cierre de dependencias de `roots` (hashes). Cada función se
        renombra a f_<hash> y las llamadas se reescriben por hash, no por nombre actual."""
        fns: dict[str, Fn] = {}
        pending = list(roots)
        while pending:
            h = pending.pop()
            if h in fns:
                continue
            row = self.function(h)
            fn = parse(row["source"]).fns[0]
            deps = json.loads(row["deps"])
            mapping = {n: f"f_{short(dh)}" for n, dh in deps.items()}
            mapping[fn.name] = f"f_{short(h)}"
            _rewrite_fn(fn, mapping)
            fn.name = f"f_{short(h)}"
            fns[h] = fn
            pending.extend(dh for dh in deps.values() if dh not in fns)
        alias = {}
        for r in self.db.execute("SELECT name, hash FROM names").fetchall():
            alias[r["name"]] = f"f_{short(r['hash'])}"
        return Program(list(fns.values())), alias

    def program_of_names(self) -> tuple[Program, dict[str, str]]:
        roots = [r["hash"] for r in self.db.execute("SELECT hash FROM names").fetchall()]
        return self.load_closure(roots)

    # ---------- añadir y verificar ----------
    def add(self, src: str) -> list[dict]:
        """Comprueba el fichero, hashea, verifica lo no certificado y actualiza alias."""
        program = parse(src)
        Checker(program).check()
        hashes = hash_program(program)
        # Se guarda el texto reimpreso, no el original: tiene que ser el mismo programa que
        # el hasheado, o el certificado acreditaría otra función (regresión 2026-09-05: un
        # `forall` operando perdía los paréntesis y `f([])` pasaba a cumplir su ensures).
        reimpreso = parse("\n\n".join(unparse_fn(f) for f in program.fns))
        for name, h in hash_program(reimpreso).items():
            if hashes[name] != h:
                raise SelloError("E501", f"the canonical text of `{name}` reparses to a different function; nothing was stored")
        interp = Interpreter(program)
        out: list[dict] = []
        deps_of = {f.name: {n: hashes[n] for n in callees(f)} for f in program.fns}
        for fn in program.fns:
            h = hashes[fn.name]
            self.db.execute(
                "INSERT OR IGNORE INTO functions VALUES (?,?,?,?,?,?,?,?,?,?)",
                (h, fn.name, unparse_fn(fn), signature(fn), str(fn.ret), fn.effects,
                 json.dumps([unparse(r) for r in fn.requires]), json.dumps([unparse(e) for e in fn.ensures]),
                 json.dumps(deps_of[fn.name]), _now()))
            cert = self.certificate(h)
            if cert and cert["ok"]:
                out.append({"name": fn.name, "hash": short(h), "cached": True, "certificate": cert})
                self._alias(fn.name, h)
                continue
            try:
                n = run_examples(Program([fn]), interp)
                self.db.execute("INSERT OR REPLACE INTO certificates VALUES (?,?,?,?,?,?)",
                                (h, 1, 1, n, _now(), None))
                self._alias(fn.name, h)
                out.append({"name": fn.name, "hash": short(h), "cached": False, "certificate": self.certificate(h)})
            except SelloError as e:
                self.db.execute("INSERT OR REPLACE INTO certificates VALUES (?,?,?,?,?,?)",
                                (h, 1, 0, 0, _now(), json.dumps(e.to_dict())))
                self.db.commit()
                raise
        self.db.commit()
        return out

    def _alias(self, name: str, h: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO names VALUES (?,?,?)", (name, h, _now()))

    def verify(self, name: str) -> dict:
        """Vuelve a verificar aunque haya certificado. Para comprobar que el almacén no miente."""
        h = self.resolve(name)
        program, _ = self.load_closure([h])
        Checker(program).check()
        target = next(f for f in program.fns if f.name == f"f_{short(h)}")
        try:
            n = run_examples(Program([target]), Interpreter(program))
            self.db.execute("INSERT OR REPLACE INTO certificates VALUES (?,?,?,?,?,?)", (h, 1, 1, n, _now(), None))
        except SelloError as e:
            self.db.execute("INSERT OR REPLACE INTO certificates VALUES (?,?,?,?,?,?)", (h, 1, 0, 0, _now(), json.dumps(e.to_dict())))
            self.db.commit()
            raise
        self.db.commit()
        return {"name": name, "hash": short(h), "certificate": self.certificate(h)}

    def eval(self, expr_src: str):
        from .interp import fmt
        from .parser import parse_expr
        program, alias = self.program_of_names()
        expr = parse_expr(expr_src)
        _rewrite_calls(expr, alias)
        ck = Checker(program); ck.fns = {f.name: f for f in program.fns}
        ck.type_of(expr, {}, None)
        return fmt(Interpreter(program).eval(expr, {}, None))
