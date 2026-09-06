"""Servidor MCP: la API de lectura del almacén y el compilador, para agentes.

La sintaxis de lectura de Sello es una API, no un fichero: `sig`, `deps`, `users`, `names`,
`verify`, `eval`, más `check` y `add`. Este módulo la sirve por MCP (stdio) con exactamente
las mismas respuestas JSON que la CLI, y añade `sello_spec`: la especificación, que es el
prompt que un modelo debe leer antes de escribir Sello.

    uv run sello mcp --store .sello/store.db

Glue sin tests (política de QA del repo); la lógica que sirve ya está testeada en el almacén
y el compilador.
"""

from __future__ import annotations

import functools
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from .compile import check_source
from .errors import SelloError
from .store import Store

SPEC = Path(__file__).resolve().parents[1] / "spec" / "SPEC.md"


def _guard(f):
    """La misma disciplina que la CLI: un SelloError es una respuesta, no una excepción.
    `wraps` conserva la firma, que es de donde MCP saca el esquema de la tool."""
    @functools.wraps(f)
    def run(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except SelloError as e:
            return {"ok": False, "error": e.to_dict()}
    return run


def build(store_path: str) -> MCPServer:
    """El servidor con sus tools. El almacén se abre por llamada: sqlite no comparte conexiones
    entre hilos y así cada tool ve lo último."""
    server = MCPServer(
        "sello",
        instructions="Sello is a programming language whose user is an AI. Call sello_spec first "
                     "and read it before writing Sello. Every answer is the same JSON the `sello` "
                     "CLI prints: {ok: true, ...} or {ok: false, error: {code, where, what, fix}}.",
    )

    def store() -> Store:
        return Store(store_path)

    @server.tool()
    def sello_spec() -> dict:
        """The Sello language specification (two pages). Read it before writing any Sello code."""
        if not SPEC.exists():
            return {"ok": False, "error": {"code": "E501", "what": f"spec not found at {SPEC}"}}
        return {"ok": True, "spec": SPEC.read_text()}

    @server.tool()
    @_guard
    def sello_check(source: str) -> dict:
        """Parse, typecheck, run the examples and prove the contracts of a Sello program (source text). Nothing is stored."""
        return check_source(source)

    @server.tool()
    @_guard
    def sello_add(source: str) -> dict:
        """Check a Sello program and add its functions to the store, each with its certificate. Names become aliases of the hashes."""
        return {"ok": True, "added": store().add(source)}

    @server.tool()
    @_guard
    def sello_sig(name: str) -> dict:
        """Signature, requires, ensures, effects and certificate of a stored function, without its body."""
        return {"ok": True, **store().sig(name)}

    @server.tool()
    @_guard
    def sello_view(name: str) -> dict:
        """Canonical source text of a stored function."""
        return {"ok": True, **store().view(name)}

    @server.tool()
    @_guard
    def sello_deps(name: str) -> dict:
        """Functions that a stored function calls."""
        return {"ok": True, "name": name, "deps": store().deps(name)}

    @server.tool()
    @_guard
    def sello_users(name: str) -> dict:
        """Functions that call a stored function."""
        return {"ok": True, "name": name, "users": store().users(name)}

    @server.tool()
    @_guard
    def sello_names() -> dict:
        """Every name in the store with its hash and signature."""
        return {"ok": True, "names": store().names()}

    @server.tool()
    @_guard
    def sello_verify(name: str) -> dict:
        """Re-run verification of a stored function (examples and prover) and refresh its certificate."""
        return {"ok": True, **store().verify(name)}

    @server.tool()
    @_guard
    def sello_eval(expr: str) -> dict:
        """Evaluate a Sello expression against the store, e.g. max_of([factorial(3), div(9, 2)]). Contracts are checked on every call."""
        return {"ok": True, "value": store().eval(expr)}

    return server


def serve(store_path: str = ".sello/store.db") -> None:
    build(store_path).run(transport="stdio")
