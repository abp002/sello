#!/usr/bin/env python3
"""Baja el benchmark de vericoding a una caché fuera del repo. Fase 4.

Solo `raw.githubusercontent.com` pasa el proxy (la API de GitHub y Hugging Face, no;
2026-09-06), así que se baja fichero a fichero: el CSV de metadatos y, de él, las specs
Dafny (`specs/<ID>_specs.dfy`, 3.029). Lo ya bajado no se vuelve a pedir.

    uv run python bench/vericoding/bajar.py                 # CSV + todas las specs Dafny
    uv run python bench/vericoding/bajar.py DA0001 DD0003   # solo esas

Caché: `bench/vericoding/cache/` (en .gitignore). Las tareas traducidas que sí van al repo
las escribe `traducir.py`.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

AQUI = Path(__file__).resolve().parent
CACHE = AQUI / "cache"
SPECS = CACHE / "specs"
CSV = CACHE / "vericoding_benchmark_v1.csv"
RAW = "https://raw.githubusercontent.com/Beneficial-AI-Foundation/vericoding-benchmark/main"


def bajar(url: str, destino: Path, intentos: int = 4) -> bool:
    """GET a `destino`; False si no existe (404) o no responde tras los reintentos."""
    if destino.exists() and destino.stat().st_size > 0:
        return True
    destino.parent.mkdir(parents=True, exist_ok=True)
    espera = 2.0
    for i in range(intentos):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                destino.write_bytes(r.read())
            return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            err: Exception = e
        except Exception as e:  # red, proxy
            err = e
        if i + 1 < intentos:
            time.sleep(espera)
            espera *= 2
    print(f"  {url}: {err}", file=sys.stderr)
    return False


def metadatos() -> list[dict]:
    """Las 12.504 filas del CSV (id, language, source, source-id, qa-issue, ...)."""
    if not bajar(f"{RAW}/vericoding_benchmark_v1.csv", CSV):
        raise SystemExit("no se pudo bajar el CSV")
    return list(csv.DictReader(CSV.open()))


def spec(id_: str) -> Path | None:
    p = SPECS / f"{id_}_specs.dfy"
    return p if bajar(f"{RAW}/specs/{id_}_specs.dfy", p) else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*", help="ids concretos (por defecto, todas las Dafny)")
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()
    filas = metadatos()
    ids = args.ids or [r["id"] for r in filas if r["language"] == "dafny"]
    print(f"{len(ids)} specs -> {SPECS}", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        hechos = list(ex.map(spec, ids))
    faltan = [i for i, p in zip(ids, hechos) if p is None]
    print(f"bajadas {len(ids) - len(faltan)}, sin bajar {len(faltan)}" + (f": {' '.join(faltan[:10])}" if faltan else ""),
          file=sys.stderr)
    return 1 if faltan else 0


if __name__ == "__main__":
    sys.exit(main())
