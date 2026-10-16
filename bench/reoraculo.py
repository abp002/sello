#!/usr/bin/env python3
"""Vuelve a pasar el oráculo sobre los cuerpos ya entregados de una corrida de `harness3.py`, sin
llamar al modelo. Para corregir una medida cuando cambia el oráculo y no las soluciones (issue #2:
tope por caso en Sello) o el intérprete (issue #4: memoizar). Escribe `<fichero>-<sufijo>.jsonl`
al lado; el sufijo es `reoraculo` salvo que se pase `--sufijo`.

    SELLO_BATERIA=nuevas .venv/bin/python bench/reoraculo.py resultados/juez-...-sel9-S-a.jsonl ...
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import harness3 as h3
import juez


def main() -> int:
    args, sufijo = sys.argv[1:], "reoraculo"
    if args[:1] == ["--sufijo"]:
        sufijo, args = args[1], args[2:]
    for f in map(Path, args):
        out = []
        for r in map(json.loads, f.read_text().splitlines()):
            if r.get("accepted_at"):
                p = json.loads((h3.PROBLEMAS / f"{r['problem']}.json").read_text())
                c = h3.ejecutar(r["cond"], r["code"], p, p["oracle"])
                casos = c if isinstance(c, list) else [{**x, "result": juez.REJECT, "detail": c} for x in p["oracle"]]
                antes, r["oracle"] = r["oracle"], juez.contar(casos)
                r["oracle_cases"] = casos
                if antes != r["oracle"]:
                    print(f"{f.name[-14:-6]} {r['problem']}: ruidosos dom {antes['dom_ruidoso']} -> "
                          f"{r['oracle']['dom_ruidoso']}, silenciosos dom {antes['dom_silencioso']} -> "
                          f"{r['oracle']['dom_silencioso']}", flush=True)
            out.append(json.dumps(r, ensure_ascii=False))
        f.with_name(f"{f.stem}-{sufijo}.jsonl").write_text("\n".join(out) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
