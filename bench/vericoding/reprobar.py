#!/usr/bin/env python3
"""Vuelve a pasar el probador por los programas de corridas de harness4. Sin modelo.

Para medir un cambio del probador sin pagar otra corrida: cada intento aceptado (fase `unproven`
o `proven`) de cada tarea se recomprueba con el probador actual, con el mismo criterio de éxito
que harness4 (la principal y todo lo que llama, sin los helpers congelados, en nivel 2). La
tarea queda probada en el primer intento que ahora lo está. Es una cota inferior: si el modelo
hubiera recibido otro motivo, habría escrito otra cosa en los intentos siguientes; lo que
sigue sin probarse puede que se hubiera probado.

    uv run python bench/vericoding/reprobar.py bench/resultados/vericoding-...jsonl [...] --etiqueta X

Escribe `reprobar-<fecha>-<etiqueta>.{jsonl,md}` en bench/resultados.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
sys.path.insert(0, str(AQUI))

from harness import RESULTADOS  # noqa: E402
from harness4 import veredicto  # noqa: E402
from probador import comprobar, motivo  # noqa: E402


def reprobar(fila: dict) -> dict:
    """La tarea con sus intentos aceptados recomprobados."""
    congelados = set(fila.get("helpers") or [])
    proven_at = principal_at = None
    ultimo_motivo = ""
    for a in fila.get("detail", []):
        if a.get("fase") not in ("unproven", "proven") or not a.get("code"):
            continue
        vd = veredicto(comprobar(a["code"]), a["code"], fila["fn"], congelados)
        if vd["fase"] == "compile":  # no debería: el intento compiló con el probador de entonces
            ultimo_motivo = f"compile: {vd['error'].get('code')}"
            continue
        if vd["principal"] == 2:
            principal_at = principal_at or a["n"]
        if vd["fase"] == "proven":
            proven_at = a["n"]
            break
        ultimo_motivo = next(iter(vd["motivos"].values()), "")
    return {"problem": fila["problem"], "fn": fila["fn"], "model": fila["model"],
            "antes": fila.get("proven_at"), "ahora": proven_at,
            "principal_antes": fila.get("principal_proven_at"), "principal_ahora": principal_at,
            "motivo": "" if proven_at else ultimo_motivo}


class Carga:
    """Load average de la máquina durante la pasada, muestreado cada 10 s. Con carga, el reloj de
    red del probador corta más y decide resultados (ALE-188: con una compilación ajena en marcha,
    50 cortes y 3 tareas menos; sin ella, 5 cortes y 0 cambios entre pasadas)."""

    def __init__(self) -> None:
        self.muestras = [os.getloadavg()[0]]
        self._fin = threading.Event()
        self._hilo = threading.Thread(target=self._muestrea, daemon=True)
        self._hilo.start()

    def _muestrea(self) -> None:
        while not self._fin.wait(10):
            self.muestras.append(os.getloadavg()[0])

    def cierra(self) -> list[str]:
        self._fin.set()
        self.muestras.append(os.getloadavg()[0])
        ini, top, fin = self.muestras[0], max(self.muestras), self.muestras[-1]
        lineas = [f"Carga de la máquina (load average de 1 min): al empezar {ini:.1f}, máximo {top:.1f}, "
                  f"al acabar {fin:.1f}; {os.cpu_count()} núcleos."]
        if top > (os.cpu_count() or 1):
            lineas.append("\n**Aviso: la máquina iba cargada.** El reloj de red del probador pudo decidir "
                          "resultados: esta pasada no sirve para medir un cambio.")
        return lineas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("corridas", nargs="+", type=Path)
    ap.add_argument("--etiqueta", required=True)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    cuando = dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    base = RESULTADOS / f"reprobar-{cuando}-{a.etiqueta}"
    md = [f"# Reprobar {cuando} ({a.etiqueta})\n",
          "Los programas aceptados de cada corrida, recomprobados con el probador de este commit. Sin modelo.\n",
          "| Corrida | probadas antes | probadas ahora | principal antes | principal ahora | ganadas | perdidas |",
          "|---|---|---|---|---|---|---|"]
    cambios: list[str] = []
    reloj = 0
    carga = Carga()
    with open(f"{base}.jsonl", "w") as out, ThreadPoolExecutor(a.workers) as ex:
        for corrida in a.corridas:
            filas = [json.loads(x) for x in corrida.read_text().splitlines() if x.strip()]
            filas = [f for f in filas if not f.get("sin_respuesta")]
            res = list(ex.map(reprobar, filas))
            for r in res:
                out.write(json.dumps({"corrida": corrida.name, **r}, ensure_ascii=False) + "\n")
            ganadas = [r for r in res if r["ahora"] and not r["antes"]]
            perdidas = [r for r in res if r["antes"] and not r["ahora"]]
            n = len(res)
            md.append(f"| {corrida.stem} | {sum(1 for r in res if r['antes'])}/{n} | "
                      f"**{sum(1 for r in res if r['ahora'])}/{n}** | "
                      f"{sum(1 for r in res if r['principal_antes'])}/{n} | {sum(1 for r in res if r['principal_ahora'])}/{n} | "
                      f"{len(ganadas)} | {len(perdidas)} |")
            cambios += [f"- {corrida.stem}: **ganada** {r['problem']} `{r['fn']}` (intento {r['ahora']})" for r in ganadas]
            cambios += [f"- {corrida.stem}: **perdida** {r['problem']} `{r['fn']}`: {motivo(r['motivo'])} ({r['motivo'][:120]})"
                        for r in perdidas]
            reloj += sum(1 for r in res if "(wall clock)" in r["motivo"])
            print(md[-1], file=sys.stderr, flush=True)
    md += ["", *carga.cierra(), f"Tareas cuyo motivo final lleva «(wall clock)»: {reloj}."]
    md += ["", "## Cambios", ""] + (cambios or ["Ninguno."])
    Path(f"{base}.md").write_text("\n".join(md) + "\n")
    print(f"{base}.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
