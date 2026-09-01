"""CLI de Sello. Toda la salida es JSON: el usuario es un agente."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .checker import Checker
from .compile import check_source, compile_source, run_examples
from .errors import SelloError
from .interp import fmt
from .parser import parse_expr
from .store import Store


def _store(args: argparse.Namespace) -> Store:
    return Store(args.store)


def _guard(f):
    def run(args: argparse.Namespace) -> int:
        try:
            return _out(f(args))
        except SelloError as e:
            return _out({"ok": False, "error": e.to_dict()}, 1)
    return run


@_guard
def cmd_add(args):
    return {"ok": True, "added": _store(args).add(Path(args.file).read_text())}


@_guard
def cmd_sig(args):
    return {"ok": True, **_store(args).sig(args.name)}


@_guard
def cmd_view(args):
    return {"ok": True, **_store(args).view(args.name)}


@_guard
def cmd_deps(args):
    return {"ok": True, "name": args.name, "deps": _store(args).deps(args.name)}


@_guard
def cmd_users(args):
    return {"ok": True, "name": args.name, "users": _store(args).users(args.name)}


@_guard
def cmd_names(args):
    return {"ok": True, "names": _store(args).names()}


@_guard
def cmd_verify(args):
    return {"ok": True, **_store(args).verify(args.name)}


@_guard
def cmd_eval(args):
    return {"ok": True, "value": _store(args).eval(args.expr)}


def _out(d: dict, code: int = 0) -> int:
    print(json.dumps(d, ensure_ascii=False, indent=2))
    return code


def cmd_check(args: argparse.Namespace) -> int:
    src = Path(args.file).read_text()
    try:
        return _out(check_source(src))
    except SelloError as e:
        return _out({"ok": False, "error": e.to_dict()}, 1)


def _load(args: argparse.Namespace):
    src = Path(args.file).read_text()
    program, interp = compile_source(src)
    run_examples(program, interp)
    ck = Checker(program)
    ck.fns = {f.name: f for f in program.fns}
    return program, interp, ck


def cmd_run(args: argparse.Namespace) -> int:
    try:
        program, interp, ck = _load(args)
        expr = parse_expr(args.expr)
        ck.type_of(expr, {}, None)
        return _out({"ok": True, "value": fmt(interp.eval(expr, {}, None))})
    except SelloError as e:
        return _out({"ok": False, "error": e.to_dict()}, 1)


def cmd_test(args: argparse.Namespace) -> int:
    """Casos ocultos: [{"call": "f(1, 2)", "expect": "3"}, ...]. Es lo que usa el harness."""
    try:
        program, interp, ck = _load(args)
    except SelloError as e:
        return _out({"ok": False, "error": e.to_dict()}, 1)
    cases = json.loads(Path(args.cases).read_text())
    failed: list[dict] = []
    for c in cases:
        try:
            call = parse_expr(c["call"])
            ck.type_of(call, {}, None)
            got = fmt(interp.eval(call, {}, None))
            expected = fmt(interp.eval(parse_expr(c["expect"]), {}, None))
            if got != expected:
                failed.append({"call": c["call"], "expected": expected, "got": got})
        except SelloError as e:
            failed.append({"call": c["call"], "error": e.to_dict()})
    return _out({"ok": not failed, "passed": len(cases) - len(failed), "total": len(cases),
                 "failed": failed}, 1 if failed else 0)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="sello", description="Sello: un lenguaje cuyo usuario es la IA")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="parse, typecheck and run examples"); c.add_argument("file"); c.set_defaults(f=cmd_check)
    r = sub.add_parser("run", help="evaluate an expression"); r.add_argument("file"); r.add_argument("expr"); r.set_defaults(f=cmd_run)
    t = sub.add_parser("test", help="run hidden cases"); t.add_argument("file"); t.add_argument("cases"); t.set_defaults(f=cmd_test)
    for name, fn, extra, help_ in [
        ("add", cmd_add, ["file"], "check a file and add its functions to the store"),
        ("sig", cmd_sig, ["name"], "signature + contract + certificate, no body"),
        ("view", cmd_view, ["name"], "canonical source of a function"),
        ("deps", cmd_deps, ["name"], "functions this one calls"),
        ("users", cmd_users, ["name"], "functions that call this one"),
        ("names", cmd_names, [], "every name in the store"),
        ("verify", cmd_verify, ["name"], "re-run verification and refresh the certificate"),
        ("eval", cmd_eval, ["expr"], "evaluate an expression against the store"),
    ]:
        sp = sub.add_parser(name, help=help_)
        for a in extra:
            sp.add_argument(a)
        sp.add_argument("--store", default=".sello/store.db")
        sp.set_defaults(f=fn)
    args = p.parse_args(argv)
    return args.f(args)


if __name__ == "__main__":
    sys.exit(main())
