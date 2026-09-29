"""El almacén: funciones por hash, nombres como alias, certificados por hash.

Verificada una vez, verificada para siempre: un hash probado (nivel 2) no se vuelve a
verificar. Uno de nivel 1 sí se reintenta en cada `add`, por si ahora se prueba (ALE-171). Como el hash de un llamador incluye el hash del llamado, cambiar una
dependencia invalida solo a quien la usa. El nivel 2 es modular: lo que da por bueno se lee
en su cierre (`closure`).

Un contrato puede entrar sin cuerpo, `{ sorry }`: es un hueco, y su hash es el de su contrato
(`contract_hashes`). Lo rellena la función que, con el cuerpo cambiado por `sorry`, da ese hash.
El contrato es de quien lo escribe (`origins`): solo su autor le cambia el contrato a ese nombre.
"""

from __future__ import annotations

import copy
import datetime as dt
import json
import sqlite3
from pathlib import Path

from .checker import Checker, signature
from .compile import level, run_examples
from .errors import SelloError
from .hash import _sccs, callees, contract_hashes, hash_program, short
from .interp import Interpreter
from .nodes import Call, Expr, Fn, Program
from .parser import parse
from .pretty import unparse, unparse_fn
from .prover import PROVEN, Verdict, prove_program

SCHEMA = """
CREATE TABLE IF NOT EXISTS functions (
  hash TEXT PRIMARY KEY, name TEXT, source TEXT, signature TEXT, ret TEXT, effects TEXT,
  requires TEXT, ensures TEXT, deps TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS names (name TEXT PRIMARY KEY, hash TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS certificates (
  hash TEXT PRIMARY KEY, level INTEGER, ok INTEGER, examples INTEGER, verified_at TEXT, error TEXT,
  pending INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS origins (
  hash TEXT PRIMARY KEY, contract TEXT, contract_author TEXT, body_author TEXT);
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
        # Los almacenes de antes de los huecos (2026-09-29) no tienen ejemplos pendientes.
        if "pending" not in {r["name"] for r in self.db.execute("PRAGMA table_info(certificates)")}:
            self.db.execute("ALTER TABLE certificates ADD COLUMN pending INTEGER NOT NULL DEFAULT 0")
            self.db.commit()

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
        d = {"level": row["level"], "ok": bool(row["ok"]), "examples": row["examples"]}
        if row["pending"]:
            d["pending"] = row["pending"]  # ejemplos que llegan a un hueco: ni pasan ni fallan
        d["verified_at"] = row["verified_at"]
        if row["error"]:
            d["error"] = json.loads(row["error"])
        return d

    def origin(self, h: str) -> sqlite3.Row | None:
        """Contrato y autores de `h`. None en lo guardado antes de los huecos."""
        return self.db.execute("SELECT * FROM origins WHERE hash = ?", (h,)).fetchone()

    def is_hole(self, h: str) -> bool:
        """Un hueco es su propio contrato."""
        o = self.origin(h)
        return o is not None and o["contract"] == h

    def _authorship(self, h: str) -> dict:
        """Lo que se sabe del origen de `h`: si es un hueco o qué hueco rellena, y quién escribió
        su contrato y su cuerpo."""
        o = self.origin(h)
        if o is None:
            return {}
        d: dict = {}
        if o["contract"] == h:
            d["hole"] = True
        elif self.is_hole(o["contract"]):
            d["implements"] = short(o["contract"])
        if o["contract_author"] is not None:
            d["contract_author"] = o["contract_author"]
        if o["body_author"] is not None:
            d["body_author"] = o["body_author"]
        return d

    def closure(self, h: str) -> dict:
        """Lo que el certificado de `h` da por bueno. El nivel 2 es modular (se prueba con los
        contratos de lo que se llama), así que vale lo que valga lo más flojo de su cierre, como
        un teorema de Lean vale lo que los `sorry` que lista `#print axioms`. `closure_level` es
        el nivel más bajo entre `h` y todo lo que alcanza por sus deps, helpers de los contratos
        incluidos; `rests_on`, lo de ese cierre que no llega a 2 (0: su verificación falló). Se
        calcula al leer y no se guarda: el certificado de una dependencia puede subir con
        `verify` o con otro `add` (ALE-171)."""
        level, rests_on = 2, []
        seen, pending = {h}, [h]
        while pending:
            x = pending.pop()
            row, cert = self.function(x), self.certificate(x)
            lv = cert["level"] if cert and cert["ok"] else 0
            level = min(level, lv)
            if x != h and lv < 2:
                rests_on.append({"name": row["name"], "hash": short(x), "level": lv,
                                 **({"hole": True} if self.is_hole(x) else {})})
            for dh in json.loads(row["deps"]).values():
                if dh not in seen:
                    seen.add(dh)
                    pending.append(dh)
        return {"closure_level": level, "rests_on": sorted(rests_on, key=lambda d: (d["name"], d["hash"]))}

    def _report(self, h: str) -> dict | None:
        """El certificado tal como se lee: lo guardado más su cierre."""
        cert = self.certificate(h)
        return cert and {**cert, **self.closure(h)}

    def names(self) -> list[dict]:
        rows = self.db.execute("SELECT n.name, n.hash, f.signature FROM names n JOIN functions f ON f.hash = n.hash ORDER BY n.name").fetchall()
        return [{"name": r["name"], "hash": short(r["hash"]), "signature": r["signature"],
                 **({"hole": True} if self.is_hole(r["hash"]) else {})} for r in rows]

    def sig(self, name: str) -> dict:
        """Firma + contrato + certificado. Sin cuerpo: es lo que lee la IA."""
        h = self.resolve(name)
        f = self.function(h)
        return {"name": name, "hash": short(h), "signature": f["signature"],
                "requires": json.loads(f["requires"]), "ensures": json.loads(f["ensures"]),
                "effects": f["effects"], **self._authorship(h), "certificate": self._report(h)}

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

    def _named_on(self, h: str) -> list[dict]:
        """Los nombres cuya función alcanza `h` por sus deps, sin ser `h`. Al rellenar un hueco,
        los que siguen llamándolo: su hash lleva el del hueco y hay que añadirlos otra vez."""
        rows = self.db.execute("SELECT name, hash FROM names ORDER BY name").fetchall()
        return [{"name": r["name"], "hash": short(r["hash"])} for r in rows
                if r["hash"] != h and self._reaches(r["hash"], h)]

    def _reaches(self, start: str, target: str) -> bool:
        seen, pending = {start}, [start]
        while pending:
            for dh in json.loads(self.function(pending.pop())["deps"]).values():
                if dh == target:
                    return True
                if dh not in seen:
                    seen.add(dh)
                    pending.append(dh)
        return False

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

    def link(self, program: Program) -> tuple[Program, dict[str, str]]:
        """Enlaza un fuente con el almacén. Lo que el fuente llama y no define se resuelve por
        su alias y entra con su cierre de dependencias (`load_closure`, renombrado a f_<hash>).
        Devuelve el programa para comprobar, ejecutar y probar (lo del almacén más una copia
        del fuente con esas llamadas reescritas) y el hash completo de cada nombre enlazado,
        para `hash_program`. El fuente no se toca: se guarda con los nombres que escribió
        quien lo escribió. Un nombre que tampoco está en el almacén se deja y el checker da E401."""
        defined = {f.name for f in program.fns}
        called = sorted({n for f in program.fns for n in callees(f)} - defined)
        external: dict[str, str] = {}
        for n in called:
            row = self.db.execute("SELECT hash FROM names WHERE name = ?", (n,)).fetchone()
            if row is not None:
                external[n] = row["hash"]
        if not external:
            return program, {}
        lib, _ = self.load_closure(list(external.values()))
        own = copy.deepcopy(program.fns)
        mapping = {n: f"f_{short(h)}" for n, h in external.items()}
        for fn in own:
            _rewrite_fn(fn, mapping)
        return Program(lib.fns + own), external

    def program_of_names(self) -> tuple[Program, dict[str, str]]:
        roots = [r["hash"] for r in self.db.execute("SELECT hash FROM names").fetchall()]
        return self.load_closure(roots)

    # ---------- añadir y verificar ----------
    def add(self, src: str, author: str | None = None) -> list[dict]:
        """Comprueba el fichero, hashea, verifica lo no certificado y actualiza alias. `author`
        firma los contratos nuevos y los cuerpos; el contrato de un hueco sigue siendo de su autor."""
        program = parse(src)
        linked, external = self.link(program)
        Checker(linked).check()
        own = {f.name: f for f in linked.fns if f.name in {g.name for g in program.fns}}
        hashes = hash_program(program, external)
        # Se guarda el texto reimpreso, no el original: tiene que ser el mismo programa que
        # el hasheado, o el certificado acreditaría otra función (regresión 2026-09-05: un
        # `forall` operando perdía los paréntesis y `f([])` pasaba a cumplir su ensures).
        reimpreso = parse("\n\n".join(unparse_fn(f) for f in program.fns))
        for name, h in hash_program(reimpreso, external).items():
            if hashes[name] != h:
                raise SelloError("E501", f"the canonical text of `{name}` reparses to a different function; nothing was stored")
        contracts = contract_hashes(program, external)
        self._guard(program, contracts, author)
        interp = Interpreter(linked)
        fns = {f.name: f for f in program.fns}
        deps_of = {f.name: {n: hashes[n] for n in callees(f)} for f in program.fns}
        cached: dict[str, bool] = {}
        verdicts: dict[str, Verdict] | None = None  # el probador, solo si hace falta verificar algo
        # Lo llamado antes que quien lo llama, y cada ciclo entero antes de darle alias: si algo
        # falla, nada de lo que lo alcanza se queda guardado (regresión 2026-09-29: en el orden
        # del fichero, un llamador que iba delante se quedaba con alias y nivel 2 sobre un
        # llamado que después fallaba).
        for comp in _sccs({n: set(d) for n, d in deps_of.items()}):
            for name in comp:
                fn, h = fns[name], hashes[name]
                self.db.execute(
                    "INSERT OR IGNORE INTO functions VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (h, fn.name, unparse_fn(fn), signature(fn), str(fn.ret), fn.effects,
                     json.dumps([unparse(r) for r in fn.requires]), json.dumps([unparse(e) for e in fn.ensures]),
                     json.dumps(deps_of[fn.name]), _now()))
                self._record_origin(h, contracts[name], author)
                cert = self.certificate(h)
                cached[name] = bool(cert and cert["ok"] and cert["level"] >= 2)
                if cached[name]:
                    continue
                if verdicts is None:  # un hueco no se prueba: entra en los demás por su contrato
                    verdicts = prove_program(linked, only={n for n, f in own.items() if not f.hole})
                try:
                    self._certify(h, own[name], interp, verdicts.get(name))
                except SelloError:
                    self.db.commit()
                    raise
            for name in comp:
                self._alias(name, hashes[name])
        self.db.commit()
        return [self._added(f.name, hashes[f.name], cached[f.name]) for f in program.fns]

    def _added(self, name: str, h: str, cached: bool) -> dict:
        d = {"name": name, "hash": short(h), "cached": cached, **self._authorship(h)}
        if "implements" in d:
            on_hole = self._named_on(self.origin(h)["contract"])
            if on_hole:
                d["callers_on_hole"] = on_hole
        d["certificate"] = self._report(h)
        return d

    def _guard(self, program: Program, contracts: dict[str, str], author: str | None) -> None:
        """E103, antes de guardar nada. Un nombre cuyo contrato nació como hueco (relleno o no)
        solo cambia de contrato de la mano del autor del hueco; el cuerpo lo escribe cualquiera.
        Sin autores (None frente a None) no se bloquea nada."""
        for f in program.fns:
            row = self.db.execute("SELECT hash FROM names WHERE name = ?", (f.name,)).fetchone()
            o = row and self.origin(row["hash"])
            if not o or contracts[f.name] == o["contract"] or not self.is_hole(o["contract"]):
                continue
            owner = self.origin(o["contract"])["contract_author"]
            if author != owner:
                raise SelloError("E103", f"`{f.name}` holds the contract {short(o['contract'])}, written by "
                                 f"{owner or 'an anonymous author'}; this file changes it", f.line, f.col,
                                 f.name, {"contract": short(o["contract"]), "author": owner})

    def _record_origin(self, h: str, contract: str, author: str | None) -> None:
        """Quién escribió qué. Un hueco: el contrato, de `author`, y ningún cuerpo. Lo que rellena
        un hueco: el contrato sigue siendo del autor del hueco y el cuerpo es de `author`. Lo demás,
        las dos cosas de `author`. Como la función, el origen no cambia una vez guardado."""
        if contract == h:
            by = (author, None)
        else:
            hole = self.origin(contract) if self.is_hole(contract) else None
            by = (hole["contract_author"] if hole else author, author)
        self.db.execute("INSERT OR IGNORE INTO origins VALUES (?,?,?,?)", (h, contract, *by))

    def _certify(self, h: str, fn: Fn, interp: Interpreter, verdict: Verdict | None) -> None:
        """Ejemplos (nivel 1) y, si el probador la probó, nivel 2 (`compile.level`). Los ejemplos
        que llegan a un hueco quedan pendientes. Un fallo deja certificado fallido con el error y
        se relanza."""
        pending: list[tuple[str, str]] = []
        try:
            n = run_examples(Program([fn]), interp, pending)
            if verdict is not None and verdict.error is not None:
                raise verdict.error
        except SelloError as e:
            self._write_certificate(h, 1, False, 0, 0, json.dumps(e.to_dict()))
            raise
        proven = verdict is not None and verdict.status == PROVEN
        self._write_certificate(h, level(proven, len(pending), fn.hole), True, n, len(pending), None)

    def _write_certificate(self, h: str, lv: int, ok: bool, examples: int, pending: int,
                           error: str | None) -> None:
        self.db.execute("INSERT OR REPLACE INTO certificates (hash, level, ok, examples, pending, verified_at, error) "
                        "VALUES (?,?,?,?,?,?,?)", (h, lv, int(ok), examples, pending, _now(), error))

    def _alias(self, name: str, h: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO names VALUES (?,?,?)", (name, h, _now()))

    def verify(self, name: str) -> dict:
        """Vuelve a verificar aunque haya certificado. Para comprobar que el almacén no miente."""
        h = self.resolve(name)
        program, _ = self.load_closure([h])
        Checker(program).check()
        target = next(f for f in program.fns if f.name == f"f_{short(h)}")
        verdict = None if target.hole else prove_program(program)[target.name]
        try:
            self._certify(h, target, Interpreter(program), verdict)
        except SelloError:
            self.db.commit()
            raise
        self.db.commit()
        return {"name": name, "hash": short(h), "certificate": self._report(h)}

    def eval(self, expr_src: str):
        from .interp import fmt
        from .parser import parse_expr
        program, alias = self.program_of_names()
        expr = parse_expr(expr_src)
        _rewrite_calls(expr, alias)
        ck = Checker(program); ck.fns = {f.name: f for f in program.fns}
        ck.type_of(expr, {}, None)
        return fmt(Interpreter(program).eval(expr, {}, None))
