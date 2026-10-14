"""El contrato escrito por otro, en Python: el brazo de comparación del experimento decisivo (SEL-16).

Simétrico a `contrato.py`. El contrato es la función principal con su firma y un docstring con
condiciones en el formato que lee CrossHair (PEP 316): una línea `pre: <expresión>` por
precondición y una `post: <expresión>` por postcondición, donde `__return__` es el valor devuelto.
El cuerpo es `...`. Los helpers que llaman las condiciones van completos y se congelan con ella.

- `extraer`: el contrato de un programa (principal sin cuerpo + helpers alcanzados desde las
  condiciones, directa o transitivamente).
- `violacion`: si el programa entregado cambió la firma, el docstring o un helper congelado
  (comparados por `ast.dump`: el formato no cuenta).
- `ENFORCE`: código que el driver ejecuta tras cargar el programa y que envuelve cada función con
  condiciones para comprobarlas en cada llamada, también las recursivas: el nivel 1 de Python. Un
  `pre` violado lanza `PreconditionError` (rechazo en la frontera, como E300) y un `post`
  violado, `AssertionError` (cazado, como E201).
- `crosshair`: `crosshair check` en su propio entorno (`uvx`, trae otro Z3 que el de Sello), como
  el probador del nivel 2. Solo rechaza: devuelve el primer contraejemplo o None. CrossHair no
  prueba nada; busca entradas con un tope de tiempo.
"""

from __future__ import annotations

import ast
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

CROSSHAIR = ["uvx", "--from", "crosshair-tool==0.0.111", "crosshair", "check"]
CONDICION_S = 10   # por condición: del orden del tope de una consulta del probador
CROSSHAIR_S = 60   # por programa: el reloj del probador (PROGRAM_MS)


def condiciones(doc: str | None) -> tuple[list[str], list[str]]:
    """Las líneas `pre:` y `post:` de un docstring, en orden."""
    pres, posts = [], []
    for line in (doc or "").splitlines():
        m = re.match(r"\s*(pre|post)\s*:\s*(.+?)\s*$", line)
        if m:
            (pres if m.group(1) == "pre" else posts).append(m.group(2))
    return pres, posts


def _fns(code: str) -> dict[str, ast.FunctionDef]:
    return {n.name: n for n in ast.parse(code).body if isinstance(n, ast.FunctionDef)}


def _llamadas(src: str) -> set[str]:
    try:
        tree = ast.parse(src, mode="eval")
    except SyntaxError:
        return set()
    return {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}


@dataclass
class ContratoPy:
    principal: ast.FunctionDef   # con el cuerpo cambiado por `...`
    helpers: list[ast.FunctionDef]

    @property
    def nombres(self) -> list[str]:
        return [h.name for h in self.helpers]

    @property
    def texto(self) -> str:
        return "\n\n\n".join(ast.unparse(f) for f in [*self.helpers, self.principal])


def _sin_cuerpo(fn: ast.FunctionDef) -> ast.FunctionDef:
    doc = ast.get_docstring(fn, clean=False)
    if doc is not None:  # el formato no cuenta: ni la sangría ni las líneas en blanco
        doc = "\n".join(line.strip() for line in doc.splitlines() if line.strip())
    body: list[ast.stmt] = [ast.Expr(ast.Constant(doc))] if doc is not None else []
    return ast.FunctionDef(fn.name, fn.args, body + [ast.Expr(ast.Constant(...))], [], fn.returns,
                           None, lineno=fn.lineno, col_offset=0)


def extraer(code: str, fn: str) -> ContratoPy:
    fns = _fns(code)
    main = fns[fn]
    pres, posts = condiciones(ast.get_docstring(main))
    pendientes = set().union(*(_llamadas(c) for c in pres + posts)) if pres or posts else set()
    vistos: set[str] = set()
    while pendientes:
        n = pendientes.pop()
        if n in vistos or n == fn or n not in fns:
            continue
        vistos.add(n)
        pendientes |= {c.func.id for c in ast.walk(fns[n]) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
    helpers = [f for name, f in fns.items() if name in vistos]  # en el orden del programa
    return ContratoPy(_sin_cuerpo(main), helpers)


def _cabecera(fn: ast.FunctionDef) -> str:
    return ast.dump(ast.Module([_sin_cuerpo(fn)], []))


def violacion(c: ContratoPy, code: str) -> str | None:
    """None si el programa respeta el contrato; si no, el motivo, para el modelo."""
    try:
        fns = _fns(code)
    except SyntaxError as e:
        return f"SyntaxError: {e}"
    main = fns.get(c.principal.name)
    if main is None:
        return f"`{c.principal.name}` is missing."
    if _cabecera(main) != _cabecera(c.principal):
        return (f"The signature or the docstring of `{c.principal.name}` changed: they are the contract "
                f"and must stay exactly as given.")
    for h in c.helpers:
        if h.name not in fns or ast.dump(fns[h.name]) != ast.dump(h):
            return f"The helper `{h.name}` is part of the contract and must stay exactly as given."
    return None


ENFORCE = r'''
class PreconditionError(Exception):
    pass


def _contratar(ns):
    import functools, inspect, re
    for name, f in list(ns.items()):
        if not inspect.isfunction(f) or f.__module__ != ns.get("__name__"):
            continue
        pres, posts = [], []
        for line in (f.__doc__ or "").splitlines():
            m = re.match(r"\s*(pre|post)\s*:\s*(.+?)\s*$", line)
            if m:
                (pres if m.group(1) == "pre" else posts).append(m.group(2))
        if not pres and not posts:
            continue
        sig = inspect.signature(f)

        def envolver(f=f, sig=sig, pres=pres, posts=posts, name=name):
            @functools.wraps(f)
            def g(*a, **k):
                env = dict(sig.bind(*a, **k).arguments)
                # Todo en un solo dict de globales: con locales aparte, un generador de la condición
                # no ve los argumentos (NameError; regresión del humo de SEL-9).
                for c in pres:
                    if not eval(c, {**ns, **env}):
                        raise PreconditionError(f"{name}{tuple(a)} violates `pre: {c}`")
                r = f(*a, **k)
                env["__return__"] = r
                for c in posts:
                    if not eval(c, {**ns, **env}):
                        raise AssertionError(f"{name}{tuple(a)} returned {r!r}, which violates `post: {c}`")
                return r
            return g
        ns[name] = envolver()
'''


def crosshair(code: str, timeout: int = CROSSHAIR_S) -> str | None:
    """El primer contraejemplo de `crosshair check`, o None si no encontró ninguno a tiempo. Si
    CrossHair no llega a analizar (sale con 2, o sin salida reconocible), RuntimeError: un brazo
    de Python sin verificador en silencio inclinaría la comparación."""
    with tempfile.TemporaryDirectory() as d:
        src = Path(d, "solucion.py")
        src.write_text(code + "\n")
        try:
            r = subprocess.run([*CROSSHAIR, f"--per_condition_timeout={CONDICION_S}", str(src)],
                               capture_output=True, text=True, timeout=timeout, cwd=d)
        except subprocess.TimeoutExpired as t:
            out = t.stdout.decode() if isinstance(t.stdout, bytes) else (t.stdout or "")
            code_ = None  # el tope del programa: lo encontrado hasta ahí vale
        else:
            out, code_ = r.stdout, r.returncode
            if code_ not in (0, 1):
                raise RuntimeError(f"crosshair exit {code_}: {(r.stdout + r.stderr)[-600:]}")
    for line in out.splitlines():
        if ": error:" in line:
            return "crosshair: " + line.split(": error:", 1)[1].strip()
    if code_ == 1:
        raise RuntimeError(f"crosshair exit 1 without a counterexample line: {out[-600:]}")
    return None
