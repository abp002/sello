"""El contrato escrito por otro: se extrae de una solución aceptada y se congela.

De un programa Sello aceptado (la solución de sonnet a un problema) se toma la función
principal sin cuerpo (firma, `requires`, `ensures`, `effects`, `example`) y, completos, los
helpers que sus cláusulas usan, directa o transitivamente. Los helpers de implementación
(los que solo usa el cuerpo) se descartan: ese es el trabajo del otro modelo.

`violacion` comprueba que el programa entregado respeta el contrato congelado: la cabecera
de la principal y los helpers congelados tienen que aparecer idénticos (comparados por el
reimpresor canónico, así que el formato no cuenta). Diseño y prerregistración en el vault:
'El contrato escrito por otro caza lo que haiku deja pasar'.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cotas import llamadas  # noqa: E402

from sello.nodes import Fn  # noqa: E402
from sello.parser import parse  # noqa: E402
from sello.pretty import unparse_fn  # noqa: E402

HUECO = "  # write the body here"


@dataclass
class Contrato:
    principal: Fn
    helpers: list[Fn]  # en el orden del programa original

    @property
    def nombres(self) -> list[str]:
        return [f.name for f in self.helpers]

    @property
    def texto(self) -> str:
        """Lo que ve el modelo que escribe el cuerpo: helpers completos y la principal sin cuerpo."""
        partes = [unparse_fn(f) for f in self.helpers]
        partes.append(cabecera(self.principal) + "\n{\n" + HUECO + "\n}")
        return "\n\n".join(partes)


def cabecera(fn: Fn) -> str:
    """La función sin cuerpo, en formato canónico: todo hasta la llave."""
    return unparse_fn(fn).rsplit("\n{\n", 1)[0]


def extraer(code: str, principal: str) -> Contrato:
    prog = parse(code)
    por_nombre = {f.name: f for f in prog.fns}
    if principal not in por_nombre:
        raise ValueError(f"no hay función `{principal}` en el programa")
    main = por_nombre[principal]
    # Cierre: lo que llaman las cláusulas de la principal, y de cada helper alcanzado, sus
    # cláusulas y su cuerpo (un helper de contrato se ejecuta entero).
    pendientes: set[str] = set()
    for c in main.requires + main.ensures:
        pendientes |= llamadas(c)
    alcanzados: set[str] = set()
    while pendientes:
        n = pendientes.pop()
        if n in alcanzados or n not in por_nombre or n == principal:
            continue
        alcanzados.add(n)
        h = por_nombre[n]
        for e in h.requires + h.ensures + h.examples + [h.body]:
            pendientes |= llamadas(e)
    helpers = [f for f in prog.fns if f.name in alcanzados]
    return Contrato(main, helpers)


def violacion(contrato: Contrato, code: str) -> str | None:
    """None si `code` respeta el contrato; si no, el motivo, redactado para el modelo.
    Si `code` no parsea, None: eso lo dirá el compilador con su propio error."""
    try:
        prog = parse(code)
    except Exception:
        return None
    por_nombre = {f.name: f for f in prog.fns}
    p = contrato.principal.name
    if p not in por_nombre:
        return f"The contract is fixed: `{p}` is missing. Keep its signature and clauses exactly as given and write only its body."
    if cabecera(por_nombre[p]) != cabecera(contrato.principal):
        return (f"The contract is fixed: the signature, `requires`, `ensures`, `effects` or `example` "
                f"lines of `{p}` were changed. Restore them exactly as given; change only the body "
                f"(or add helper functions of your own).")
    for h in contrato.helpers:
        if h.name not in por_nombre:
            return f"The contract is fixed: helper `{h.name}` is missing. Include it exactly as given."
        if unparse_fn(por_nombre[h.name]) != unparse_fn(h):
            return f"The contract is fixed: helper `{h.name}` was changed. Include it exactly as given."
    return None
