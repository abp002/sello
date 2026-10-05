#!/usr/bin/env python3
"""El flujo contrato→cuerpo por el almacén y el MCP, de punta a punta.

Paso siguiente de 'El contrato se puede escribir sin el cuerpo'. Diseño, reglas y
prerregistración en el vault: 'Un hueco se rellena por el MCP igual que en el banco'. En el banco
(`harness3 --cond sello_contrato`) el contrato llega en el prompt y lo guarda `violacion`. Aquí
pasa por el producto: por cada problema, un almacén propio y dos sesiones de `claude -p` sin más
herramientas que `sello mcp`, cada una con su autor, que fija quien lanza el servidor.

  contrato  sonnet (`--author sonnet`) escribe el contrato de la principal con `{ sorry }` y lo
            guarda con `sello_add`. Con `--contratos`, en su lugar se cargan los de otra corrida
            (el control): el hueco y los helpers de sus cláusulas, con el mismo autor.
  cuerpo    haiku (`--author haiku`) recibe el enunciado, los ejemplos visibles y la noticia de
            que el almacén guarda la principal como un hueco escrito por otro. Su juez débil es
            `sello_check`; su única guarda, E103 en `sello_add`.

Después se lee el almacén. Si el nombre apunta a una función que rellena el hueco, el problema
está entregado y el oráculo de `harness3` juzga esa función, reconstruida desde el almacén con
su cierre (`programa_de`), en ejecución: sin probador, como la ejecuta `eval` (desde el
2026-10-05; nota 'El oráculo del flujo juzga lo que el almacén ejecuta'). Salen filas con el
formato de `harness3`, con la condición `sello_mcp`, que `mutantes.py` lee. De los contratos de
sonnet salen filas con el formato de `contratar.py`, que `literales.py` lee.

    uv run python bench/flujo.py --only clamp        # humo
    uv run python bench/flujo.py                     # el flujo entero
    uv run python bench/flujo.py --contratos bench/resultados/contratos-2026-09-29-2317-sonnet.jsonl
    uv run python bench/flujo.py --rejuzgar bench/resultados/flujo-A.jsonl   # solo el oráculo, sin modelo

Los servidores se lanzan con `.venv/bin/sello`, no con `uv run`. uv reinstala z3-solver en cada
arranque, porque la rueda 5.1.0.0 dice macosx_13_0 en el nombre y macosx_13_3 dentro. Con cuatro
sesiones a la vez, un servidor podría importar Z3 a mitad de la reinstalación de otro.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import RESULTADOS, ROOT  # noqa: E402
from harness3 import PROBLEMAS, cargar_contratos, ejecutar_sello, ejemplos, llamada  # noqa: E402
import contrato as ct  # noqa: E402
import juez  # noqa: E402

from sello.errors import SelloError  # noqa: E402
from sello.hash import hash_program, short  # noqa: E402
from sello.nodes import Hole, Program  # noqa: E402
from sello.parser import parse  # noqa: E402
from sello.pretty import unparse_fn  # noqa: E402
from sello.store import Store, _rewrite_fn  # noqa: E402

COND = "sello_mcp"
ORACULO = "ejecucion"  # cómo juzga el oráculo; las filas de antes del 2026-10-05 no lo dicen: fichero y probador
AUTOR_CONTRATO, AUTOR_CUERPO = "sonnet", "haiku"
MAX_TURNOS = 30
SELLO = ROOT / ".venv" / "bin" / "sello"

PREAMBULO = ("You have access to Sello, a programming language whose user is an AI, only through the "
             "`sello_*` MCP tools. You have no other tools: no files, no shell. Read the language "
             "specification with `sello_spec` before writing any Sello.\n\n")


# ---------- prompts: se escriben una vez, se prueban en humo con clamp y no se tocan ----------

def prompt_contrato(p: dict) -> str:
    return (PREAMBULO +
            f"Task: write the contract of `{p['sello']}`, not its implementation. {p['statement']} "
            f"{ejemplos(p, 'sello')}\n"
            f"Write `{p['fn']}` with its signature and its `requires`, `ensures`, `effects` and "
            f"`example` lines, and `{{ sorry }}` as its body: someone else will write the body later, "
            f"against your contract. Any helper function your clauses call must be complete, with "
            f"its own contract and body. Do not write the body of `{p['fn']}`. Store the contract "
            f"with `sello_add`.")


def prompt_cuerpo(p: dict) -> str:
    return (PREAMBULO +
            f"Task: implement `{p['sello']}`. {p['statement']} {ejemplos(p, 'sello')}\n"
            f"The store already holds `{p['fn']}` as a hole: its contract was written by someone "
            f"else. Implement it and store it with `sello_add`. You may add helper functions of "
            f"your own; every function needs its contract clauses. Tests will call `{p['fn']}`.")


# ---------- una sesión y su traza ----------

def sesion(prompt: str, model: str, store: Path, author: str, traza: Path,
           max_turnos: int = MAX_TURNOS) -> dict:
    """Una sesión de `claude -p` con solo el MCP de Sello, sin ajustes del usuario y fuera del repo
    (su CLAUDE.md no entra). Deja la traza stream-json en `traza`."""
    with tempfile.TemporaryDirectory() as d:
        config = Path(d, "mcp.json")
        config.write_text(json.dumps({"mcpServers": {"sello": {
            "command": str(SELLO), "args": ["mcp", "--store", str(store), "--author", author]}}}))
        cmd = ["claude", "-p", prompt, "--model", model, "--tools", "",
               "--mcp-config", str(config), "--strict-mcp-config", "--allowedTools", "mcp__sello",
               "--setting-sources", "", "--disable-slash-commands", "--no-chrome",
               "--no-session-persistence", "--max-turns", str(max_turnos),
               "--output-format", "stream-json", "--verbose"]
        # Sin CLAUDE_CONFIG_DIR: si no, `claude -p` hereda la cuenta 2 (bitácora del 2026-09-02).
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CONFIG_DIR"}
        carga0, t0 = os.getloadavg()[0], time.time()
        with open(traza, "w") as out:
            try:
                r = subprocess.run(cmd, stdout=out, stderr=subprocess.PIPE, text=True, cwd=d, env=env,
                                   stdin=subprocess.DEVNULL, timeout=1800)
                stderr, rc = r.stderr[-500:], r.returncode
            except subprocess.TimeoutExpired:  # la traza queda a medias y la sesión sin `result`
                stderr, rc = "timeout after 1800s", None
    ms = int((time.time() - t0) * 1000)
    return {"ms": ms, "carga": [round(carga0, 2), round(os.getloadavg()[0], 2)],
            "stderr": stderr, "returncode": rc}


def _respuesta(parte: dict) -> dict:
    c = parte.get("content")
    texto = "\n".join(x.get("text", "") for x in c if isinstance(x, dict)) if isinstance(c, list) else str(c)
    try:
        d = json.loads(texto)
        return d if isinstance(d, dict) else {"raw": texto[:500]}
    except json.JSONDecodeError:
        return {"raw": texto[:500]}


def leer_traza(path: Path) -> tuple[list[dict], dict | None]:
    """Las llamadas a Sello de una sesión, en orden, cada una con su respuesta, y el evento
    `result` (None si la sesión no llegó a darlo)."""
    usos: dict[str, dict] = {}
    orden: list[dict] = []
    final = None
    for linea in path.read_text().splitlines():
        try:
            e = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if e.get("type") == "assistant":
            for c in e["message"]["content"]:
                if c.get("type") == "tool_use":
                    x = {"tool": c["name"].removeprefix("mcp__sello__"), "input": c.get("input") or {},
                         "respuesta": None, "tool_error": False}
                    usos[c["id"]] = x
                    orden.append(x)
        elif e.get("type") == "user":
            for c in e["message"]["content"]:
                if isinstance(c, dict) and c.get("type") == "tool_result" and c.get("tool_use_id") in usos:
                    x = usos[c["tool_use_id"]]
                    x["respuesta"] = _respuesta(c)
                    x["tool_error"] = bool(c.get("is_error"))
        elif e.get("type") == "result":
            final = e
    return orden, final


def _codigo(x: dict) -> str | None:
    r = x["respuesta"] or {}
    return (r.get("error") or {}).get("code") if r.get("ok") is False else None


def programas(llamadas: list[dict]) -> list[dict]:
    """Los intentos: cada programa que el agente mandó al compilador (`check` o `add`)."""
    out = []
    for x in llamadas:
        if x["tool"] in ("sello_check", "sello_add") and "source" in x["input"]:
            r = x["respuesta"] or {}
            out.append({"n": len(out) + 1, "ok": r.get("ok") is True,
                        "phase": x["tool"].removeprefix("sello_"), "sello_error": _codigo(x),
                        "code": x["input"]["source"],
                        "feedback": json.dumps(r, ensure_ascii=False)[:2000]})
    return out


def aceptado_en(llamadas: list[dict], fn: str, h: str) -> int | None:
    """El número de programa (el de `programas`) del `add` que guardó `h` con el nombre `fn`."""
    n = 0
    for x in llamadas:
        if x["tool"] in ("sello_check", "sello_add") and "source" in x["input"]:
            n += 1
            r = x["respuesta"] or {}
            if x["tool"] == "sello_add" and r.get("ok") is True and any(
                    a.get("name") == fn and a.get("hash") == short(h) for a in r.get("added", [])):
                return n
    return None


def fricciones(llamadas: list[dict], fn: str) -> dict:
    """Lo que el paso al producto puede costar: cuántas veces choca con E103, cuántas de ellas con
    un programa que `check` ya había aceptado (check no conoce autores), y por dónde leyó el
    contrato (`sig` no enseña los ejemplos, que entran en el hash del contrato)."""
    aceptados_por_check: set[str] = set()
    e103 = tras_check = 0
    for x in llamadas:
        src = x["input"].get("source")
        if x["tool"] == "sello_check" and (x["respuesta"] or {}).get("ok") is True:
            aceptados_por_check.add(src)
        if x["tool"] == "sello_add" and _codigo(x) == "E103":
            e103 += 1
            tras_check += src in aceptados_por_check
    lee = lambda tool: sum(x["tool"] == tool and x["input"].get("name") == fn for x in llamadas)  # noqa: E731
    return {"e103": e103, "e103_tras_check": tras_check, "view": lee("sello_view"), "sig": lee("sello_sig"),
            "herramientas": dict(Counter(x["tool"] for x in llamadas)),
            "errores_herramienta": sum(x["tool_error"] for x in llamadas)}


def uso(final: dict | None) -> dict:
    """Coste, tokens, turnos y cómo acabó la sesión, del evento `result`."""
    if final is None:
        return {"cost": 0.0, "tokens_in": 0, "tokens_out": 0, "thinking": 0, "turnos": 0,
                "fin": "sin_result", "models": []}
    u = final.get("usage", {})
    return {"cost": final.get("total_cost_usd", 0.0),
            "tokens_in": u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
            + u.get("cache_read_input_tokens", 0),
            "tokens_out": u.get("output_tokens", 0),
            "thinking": (u.get("output_tokens_details") or {}).get("thinking_tokens", 0),
            "turnos": final.get("num_turns", 0), "fin": final.get("subtype"),
            "is_error": final.get("is_error"), "api_error_status": final.get("api_error_status"),
            "models": sorted(final.get("modelUsage", {})), "informe": (final.get("result") or "")[-1500:]}


# ---------- el almacén ----------

def cierre(s: Store, h: str) -> list[str]:
    """`h` y todo lo que alcanza por sus deps (helpers de los contratos incluidos), en anchura."""
    orden, vistos = [h], {h}
    i = 0
    while i < len(orden):
        for dh in json.loads(s.function(orden[i])["deps"]).values():
            if dh not in vistos:
                vistos.add(dh)
                orden.append(dh)
        i += 1
    return orden


def programa_de(s: Store, h: str, raiz: str | None = None) -> tuple[str, dict[str, str]]:
    """El programa autocontenido de `h`: su función y su cierre, por hash y no por el alias de
    ahora, cada una con el nombre con que se guardó (la raíz, con `raiz` si se da) y sus llamadas
    reescritas a esos nombres. Si dos hashes del cierre comparten nombre, los que no son la raíz
    pasan a f_<hash>. Devuelve el texto y el nombre de cada hash. El texto tiene que volver a dar
    `h`: el oráculo juzga la función guardada, no otra."""
    hashes = cierre(s, h)
    nombres = {x: s.function(x)["name"] for x in hashes}
    if raiz:
        nombres[h] = raiz
    repetidos = Counter(nombres.values())
    for x in hashes:
        if x != h and (repetidos[nombres[x]] > 1 or nombres[x] == nombres[h]):
            nombres[x] = f"f_{short(x)}"
    fns = []
    for x in reversed(hashes):
        fn = parse(s.function(x)["source"]).fns[0]
        mapping = {n: nombres[dh] for n, dh in json.loads(s.function(x)["deps"]).items()}
        mapping[fn.name] = nombres[x]
        _rewrite_fn(fn, mapping)
        fns.append(replace(fn, name=nombres[x]))
    texto = "\n\n".join(unparse_fn(f) for f in fns)
    if hash_program(parse(texto))[nombres[h]] != h:
        raise ValueError(f"el programa reconstruido de {short(h)} no vuelve a dar su hash")
    return texto, nombres


def hueco_de(s: Store, fn: str) -> str | None:
    """El hash del hueco al que apunta el nombre `fn`, o None si no apunta a un hueco."""
    row = s.db.execute("SELECT hash FROM names WHERE name = ?", (fn,)).fetchone()
    return row["hash"] if row is not None and s.is_hole(row["hash"]) else None


def relleno(s: Store, fn: str, hueco: str) -> str | None:
    """El hash de la función a la que apunta `fn` si rellena `hueco`, o None."""
    row = s.db.execute("SELECT hash FROM names WHERE name = ?", (fn,)).fetchone()
    if row is None or row["hash"] == hueco:
        return None
    o = s.origin(row["hash"])
    return row["hash"] if o is not None and o["contract"] == hueco else None


def cargar_hueco(s: Store, code: str, fn: str, author: str) -> str:
    """El control: el contrato de otra corrida, como hueco (la principal con `{ sorry }` y los
    helpers de sus cláusulas), guardado con el autor del contrato."""
    c = ct.extraer(code, fn)
    prog = Program([*c.helpers, replace(c.principal, body=Hole())])
    s.add("\n\n".join(unparse_fn(f) for f in prog.fns), author=author)
    h = hueco_de(s, fn)
    assert h is not None, f"{fn}: el contrato cargado no quedó como hueco"
    return h


def _nombres_de(s: Store, autor: str) -> list[str]:
    """Los nombres que apuntan a funciones cuyo cuerpo escribió `autor`."""
    rows = s.db.execute("SELECT n.name FROM names n JOIN origins o ON o.hash = n.hash "
                        "WHERE o.body_author = ? ORDER BY n.name", (autor,)).fetchall()
    return [r["name"] for r in rows]


# ---------- el oráculo ----------

def oraculo(code: str, p: dict) -> tuple[list[dict], dict]:
    """El oráculo de `harness3` sobre el programa reconstruido, en ejecución: los casos, con los
    contratos comprobados al ejecutar y sin probador, y sus recuentos. Por el almacén, a producción
    llega lo que `eval` ejecuta, y `eval` no vuelve a probar. Cargar el programa como fichero sí lo
    hacía, y el probador no ve lo mismo en el fichero que en el almacén. El second_largest de
    flujo-2026-10-01-1914-control, que el almacén había aceptado, no cargaba por un E201 de un
    helper, y sus 25 llamadas del dominio, correctas en ejecución, salían ruidosas. Un bug del
    dominio habría salido igual, ruidoso en vez de silencioso. Nota 'El oráculo del flujo juzga lo
    que el almacén ejecuta'."""
    r = ejecutar_sello(code, p, p["oracle"], prover=False)
    casos = [{**c, "result": juez.REJECT, "detail": r} for c in p["oracle"]] if isinstance(r, dict) else r
    return casos, juez.contar(casos)


def no_cargo(casos: list[dict]) -> bool:
    """Si el programa no llegó a cargar: entonces ninguna llamada se ejecutó y ninguna lleva `call`."""
    return bool(casos) and all("call" not in c for c in casos)


def rejuzgar(path: Path) -> list[dict]:
    """Las filas de una corrida ya hecha, con cada solución entregada juzgada de nuevo por `oraculo`,
    sin modelo, desde su `code`. Cada una guarda el oráculo con que se juzgó (`oraculo_antes`) y las
    llamadas cuyo resultado cambia. Lo demás de la fila no se toca."""
    probs = {p["fn"]: p for p in (json.loads(f.read_text()) for f in sorted(PROBLEMAS.glob("*.json")))}
    filas = []
    for line in path.read_text().splitlines():
        r = json.loads(line)
        if r.get("code"):
            p = probs[r["problem"]]
            antes = {llamada(p, c["args"]): c["result"] for c in r["oracle_cases"]}
            casos, cuenta = oraculo(r["code"], p)
            ahora = {llamada(p, c["args"]): c for c in casos}
            if antes.keys() != ahora.keys():
                raise ValueError(f"{path.name}, {r['problem']}: el oráculo del problema ya no es el de la corrida")
            cambios = [{"call": k, "zone": c["zone"], "antes": antes[k], "ahora": c["result"]}
                       for k, c in ahora.items() if antes[k] != c["result"]]
            r = {**r, "oracle": cuenta, "oracle_cases": casos,
                 "flujo": {**(r.get("flujo") or {}), "oraculo": ORACULO, "oraculo_antes": r["oracle"],
                           "no_cargo_antes": no_cargo(r["oracle_cases"]), "cambios": cambios}}
        filas.append(r)
    return filas


def resumen_rejuicio(path: Path, filas: list[dict], when: str) -> str:
    juzgadas = [r for r in filas if r.get("code")]
    fl = lambda r: r["flujo"]  # noqa: E731
    cifras = lambda o: f"{o['dom_silencioso']}+{o['amb_silencioso']} · {o['dom_ruidoso']} · {o['cazados']}"  # noqa: E731
    out = [f"# Rejuicio en ejecución de {path.stem} ({when})", "",
           "Las soluciones entregadas de la corrida, juzgadas de nuevo por el oráculo de `harness3` en "
           "ejecución: contratos comprobados al ejecutar, sin probador. Prerregistrado en el vault: 'El "
           "oráculo del flujo juzga lo que el almacén ejecuta'. Formato: silenciosos dominio+ambigua · "
           "ruidosos en el dominio · cazados.", "",
           "| Problema | antes | en ejecución | llamadas que cambian |", "|---|---|---|---|"]
    for r in sorted(juzgadas, key=lambda r: r["problem"]):
        cambios = Counter(f"{c['antes']} → {c['ahora']}" for c in fl(r)["cambios"])
        out.append(f"| {r['problem']} | {cifras(fl(r)['oraculo_antes'])} | {cifras(r['oracle'])} | "
                   + (", ".join(f"{n} {k}" for k, n in sorted(cambios.items())) or "0") + " |")
    suma = lambda k, o="oracle": sum((r[o] if o == "oracle" else fl(r)[o])[k] for r in juzgadas)  # noqa: E731
    out += ["",
            f"- Soluciones: {len(juzgadas)}; llamadas del oráculo: {sum(len(r['oracle_cases']) for r in juzgadas)}; "
            f"llamadas que cambian: {sum(len(fl(r)['cambios']) for r in juzgadas)}; soluciones con alguna: "
            f"{sum(bool(fl(r)['cambios']) for r in juzgadas)}.",
            f"- Programas que no cargan: {sum(fl(r)['no_cargo_antes'] for r in juzgadas)} → "
            f"{sum(no_cargo(r['oracle_cases']) for r in juzgadas)}.",
            f"- **Silenciosos {suma('silenciosos', 'oraculo_antes')} → {suma('silenciosos')}** (dominio "
            f"{suma('dom_silencioso', 'oraculo_antes')} → {suma('dom_silencioso')}, ambigua "
            f"{suma('amb_silencioso', 'oraculo_antes')} → {suma('amb_silencioso')}); ruidosos en el dominio "
            f"{suma('dom_ruidoso', 'oraculo_antes')} → {suma('dom_ruidoso')}; declarados en la ambigua "
            f"{suma('amb_declarado', 'oraculo_antes')} → {suma('amb_declarado')}; cazados "
            f"{suma('cazados', 'oraculo_antes')} → {suma('cazados')}."]
    return "\n".join(out) + "\n"


# ---------- las dos fases ----------

def fase_contrato(p: dict, dir_: Path, model: str) -> tuple[dict, str | None]:
    """Sonnet escribe el hueco en un almacén vacío. Devuelve su fila (formato de `contratar.py`)
    y el hash del hueco, o None si el nombre no quedó como hueco."""
    store, traza = dir_ / f"{p['fn']}-contrato.db", dir_ / f"{p['fn']}-contrato.jsonl"
    meta = sesion(prompt_contrato(p), model, store, AUTOR_CONTRATO, traza)
    llamadas, final = leer_traza(traza)
    progs = programas(llamadas)
    s = Store(store)
    hueco = hueco_de(s, p["fn"])
    code = programa_de(s, hueco, p["fn"])[0] if hueco else (progs[-1]["code"] if progs else "")
    cuerpo = False
    for x in progs:
        try:
            cuerpo |= any(f.name == p["fn"] and not f.hole for f in parse(x["code"]).fns)
        except SelloError:
            pass
    u = uso(final)
    fila = {"problem": p["fn"], "cond": "contrato", "model": model,
            "accepted_at": aceptado_en(llamadas, p["fn"], hueco) if hueco else None,
            "compila": hueco is not None, "escribio_cuerpo": cuerpo, "attempts": len(progs),
            **{k: u[k] for k in ("cost", "tokens_in", "tokens_out", "thinking")}, "ms": meta["ms"],
            "code": code, "detail": progs,
            "flujo": {"hueco": short(hueco) if hueco else None, **fricciones(llamadas, p["fn"]),
                      **{k: v for k, v in u.items() if k not in ("cost", "tokens_in", "tokens_out", "thinking")},
                      "carga": meta["carga"], "stderr": meta["stderr"], "traza": str(traza.relative_to(ROOT))}}
    print(f"  {p['fn']:<15} contrato: {'hueco ' + short(hueco) if hueco else 'SIN HUECO'} · "
          f"{len(progs)} programas · {u['turnos']} turnos · {u['fin']}", file=sys.stderr, flush=True)
    return fila, hueco


def fase_cuerpo(p: dict, dir_: Path, store: Path, hueco: str, contrato_de: dict, model: str) -> dict:
    """Haiku rellena el hueco. Devuelve su fila, con el formato de `harness3`."""
    traza = dir_ / f"{p['fn']}-cuerpo.jsonl"
    meta = sesion(prompt_cuerpo(p), model, store, AUTOR_CUERPO, traza)
    llamadas, final = leer_traza(traza)
    progs = programas(llamadas)
    fr = fricciones(llamadas, p["fn"])
    s = Store(store)
    impl = relleno(s, p["fn"], hueco)
    texto_hueco, nombres_hueco = programa_de(s, hueco, p["fn"])
    code, fns, cert = None, [], None
    if impl:
        code, nombres = programa_de(s, impl, p["fn"])
        fns = [nombres[x] for x in cierre(s, hueco)[1:] if x in nombres]
        cert = s._report(impl)
    # Si el nombre la tiene y ningún add de la traza la guardó, llegó por otra vía: se cuenta al final.
    accepted = (aceptado_en(llamadas, p["fn"], impl) or len(progs)) if impl else None
    oracle_cases: list[dict] = []
    oracle: dict = {}
    if code:
        oracle_cases, oracle = oraculo(code, p)
    u = uso(final)
    print(f"  {p['fn']:<15} cuerpo: {'rellena ' + short(impl) if impl else 'NO RELLENA'} · "
          f"{len(progs)} programas · E103 {fr['e103']} · {u['turnos']} turnos · {u['fin']}"
          + (f" · silenciosos {oracle['silenciosos']}" if oracle else ""), file=sys.stderr, flush=True)
    return {"problem": p["fn"], "cond": COND, "model": model, "accepted_at": accepted,
            "contrato": {"de": contrato_de["model"], "origen": contrato_de["origen"], "principal": p["fn"],
                         "fns": fns, "texto": texto_hueco, "hueco": short(hueco),
                         "helpers": [n for x, n in nombres_hueco.items() if x != hueco],
                         "rechazos": fr["e103"]},
            "attempts": len(progs), **{k: u[k] for k in ("cost", "tokens_in", "tokens_out", "thinking")},
            "ms": meta["ms"], "code": code, "oracle": oracle,
            "oracle_cases": oracle_cases, "detail": progs,
            "flujo": {"relleno": short(impl) if impl else None, "certificado": cert, "oraculo": ORACULO, **fr,
                      "otros_nombres": [n for n in _nombres_de(s, AUTOR_CUERPO) if n != p["fn"]],
                      **{k: v for k, v in u.items() if k not in ("cost", "tokens_in", "tokens_out", "thinking")},
                      "carga": meta["carga"], "stderr": meta["stderr"], "traza": str(traza.relative_to(ROOT))}}


def run_one(p: dict, dir_: Path, contratos: dict | None, modelo_contrato: str,
            modelo_cuerpo: str) -> tuple[dict | None, dict]:
    store = dir_ / f"{p['fn']}.db"
    fila_contrato = None
    if contratos is None:
        fila_contrato, hueco = fase_contrato(p, dir_, modelo_contrato)
        de = {"model": modelo_contrato, "origen": "mcp"}
        if hueco:  # el almacén de sonnet queda como estaba; haiku trabaja sobre una copia
            shutil.copy(dir_ / f"{p['fn']}-contrato.db", store)
    else:
        hueco = cargar_hueco(Store(store), contratos[p["fn"]]["code"], p["fn"], AUTOR_CONTRATO) \
            if p["fn"] in contratos else None
        de = {"model": contratos.get(p["fn"], {}).get("model"), "origen": contratos.get(p["fn"], {}).get("origen")}
    if hueco is None:  # sin hueco no hay nada que rellenar: no entregada, atribuida al contrato
        print(f"  {p['fn']:<15} cuerpo: no se corre (sin hueco)", file=sys.stderr, flush=True)
        return fila_contrato, {"problem": p["fn"], "cond": COND, "model": modelo_cuerpo, "accepted_at": None,
                               "sin_contrato": True, "contrato": None, "attempts": 0, "cost": 0.0,
                               "tokens_in": 0, "tokens_out": 0, "thinking": 0, "ms": 0, "code": None,
                               "oracle": {}, "oracle_cases": [], "detail": [], "flujo": {}}
    return fila_contrato, fase_cuerpo(p, dir_, store, hueco, de, modelo_cuerpo)


# ---------- resumen ----------

def resumen(contratos: list[dict], cuerpos: list[dict], when: str, tag: str) -> str:
    por = {r["problem"]: r for r in contratos}
    out = [f"# Flujo contrato→cuerpo por el MCP {when} · {tag}", "",
           "Prerregistrado en el vault: 'Un hueco se rellena por el MCP igual que en el banco'. "
           "Programas: llamadas a `sello_check` y `sello_add` con fuente. Oráculo: silenciosos "
           "dominio+ambigua · cazados.", "",
           "| Problema | contrato | cuerpo | E103 (tras check) | lee view/sig | nivel | oráculo |",
           "|---|---|---|---|---|---|---|"]
    for r in sorted(cuerpos, key=lambda r: r["problem"]):
        c = por.get(r["problem"])
        if c is None:
            cc = f"cargado ({(r.get('contrato') or {}).get('origen', '-')})"
        else:
            cc = (f"hueco en {c['accepted_at'] or '?'}/{c['attempts']}" if c["compila"] else "SIN HUECO") \
                + (" · cuerpo" if c["escribio_cuerpo"] else "")
        f = r.get("flujo") or {}
        if r.get("sin_contrato"):
            out.append(f"| {r['problem']} | {cc} | no se corre | - | - | - | - |")
            continue
        cu = (f"rellena en {r['accepted_at']}/{r['attempts']}" if r["accepted_at"] else f"NO ({r['attempts']})") \
            + (f" · {f['fin']}" if f.get("fin") != "success" else "")
        cert = f.get("certificado") or {}
        nivel = f"{cert.get('level')}/{cert.get('closure_level')}" if cert else "-"
        o = r["oracle"]
        orc = f"{o['dom_silencioso']}+{o['amb_silencioso']} · {o['cazados']}" if o else "-"
        out.append(f"| {r['problem']} | {cc} | {cu} | {f.get('e103', 0)} ({f.get('e103_tras_check', 0)}) | "
                   f"{f.get('view', 0)}/{f.get('sig', 0)} | {nivel} | {orc} |")
    corridos = [r for r in cuerpos if not r.get("sin_contrato")]
    rellenos = [r for r in cuerpos if r["accepted_at"]]
    suma = lambda k: sum(r["oracle"][k] for r in rellenos)  # noqa: E731
    fl = lambda r: r.get("flujo") or {}  # noqa: E731
    out += [""]
    if contratos:
        out += [f"- Contratos: huecos guardados {sum(c['compila'] for c in contratos)}/{len(contratos)}; "
                f"escribió cuerpo en la principal en {sum(c['escribio_cuerpo'] for c in contratos)}; programas medios "
                f"{sum(c['attempts'] for c in contratos) / max(1, len(contratos)):.2f}; tokens de salida "
                f"{sum(c['tokens_out'] for c in contratos)}; coste USD {sum(c['cost'] for c in contratos):.3f}; "
                f"sesiones que no acaban en success: {sum(fl(c).get('fin') != 'success' for c in contratos)}."]
    out += [f"- Cuerpos: rellenados {len(rellenos)}/{len(cuerpos)} (corridos {len(corridos)}); programas hasta "
            f"rellenar {sum(r['accepted_at'] for r in rellenos) / max(1, len(rellenos)):.2f}; programas por sesión "
            f"{sum(r['attempts'] for r in corridos) / max(1, len(corridos)):.2f}.",
            f"- E103: {sum(fl(r).get('e103', 0) for r in corridos)} en {sum(fl(r).get('e103', 0) > 0 for r in corridos)} "
            f"problemas; tras un check aceptado, {sum(fl(r).get('e103_tras_check', 0) for r in corridos)}. Leen el "
            f"contrato con view en {sum(fl(r).get('view', 0) > 0 for r in corridos)}, solo con sig en "
            f"{sum(fl(r).get('view', 0) == 0 and fl(r).get('sig', 0) > 0 for r in corridos)}.",
            f"- E201 en el bucle: {sum(any(x['sello_error'] == 'E201' for x in r['detail']) for r in corridos)} problemas. "
            f"Nombres propios fuera del hueco: {sum(len(fl(r).get('otros_nombres', [])) for r in corridos)}.",
            f"- Certificados: nivel 2 en {sum((fl(r).get('certificado') or {}).get('level') == 2 for r in rellenos)}, "
            f"nivel 1 en {sum((fl(r).get('certificado') or {}).get('level') == 1 for r in rellenos)}.",
            f"- Oráculo: **silenciosos {suma('silenciosos') if rellenos else 0}** (dominio "
            f"{suma('dom_silencioso') if rellenos else 0}, ambigua {suma('amb_silencioso') if rellenos else 0}); "
            f"ruidosos en el dominio {suma('dom_ruidoso') if rellenos else 0}; cazados {suma('cazados') if rellenos else 0}.",
            f"- Sesiones de haiku que no acaban en success: {sum(fl(r).get('fin') != 'success' for r in corridos)} "
            f"({', '.join(sorted({str(fl(r).get('fin')) for r in corridos if fl(r).get('fin') != 'success'})) or '-'}). "
            f"Carga máxima: {max([x for r in [*contratos, *corridos] for x in fl(r).get('carga', [0])] or [0])}.",
            f"- Modelos: {', '.join(sorted({m for r in [*contratos, *corridos] for m in fl(r).get('models', [])}))}."]
    return "\n".join(out) + "\n\n" + juez.resumen(cuerpos, AUTOR_CUERPO, when)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--contratos", type=Path,
                    help="corrida de contratar.py o del juez de la que cargar los contratos (el control)")
    ap.add_argument("--modelo-contrato", default="sonnet")
    ap.add_argument("--modelo-cuerpo", default="haiku")
    ap.add_argument("--only", help="nombre de un problema")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--rejuzgar", nargs="+", type=Path, metavar="JSONL",
                    help="corridas ya hechas: solo el oráculo, sin modelo; deja <corrida>-ejecucion.{jsonl,md}")
    args = ap.parse_args()
    if args.rejuzgar:
        when = dt.datetime.now().strftime("%Y-%m-%d-%H%M")
        for path in args.rejuzgar:
            filas = rejuzgar(path)
            base = path.with_name(f"{path.stem}-{ORACULO}")
            Path(f"{base}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in filas))
            md = resumen_rejuicio(path, filas, when)
            Path(f"{base}.md").write_text(md)
            print(md)
        return 0
    if not SELLO.exists():
        ap.error(f"falta {SELLO}: `uv sync` primero")
    probs = [json.loads(f.read_text()) for f in sorted(PROBLEMAS.glob("*.json"))]
    if args.only:
        probs = [p for p in probs if p["fn"] == args.only]
    contratos = cargar_contratos(args.contratos) if args.contratos else None
    when = dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    tag = "control" if contratos is not None else "mcp"
    base = RESULTADOS / (("humo-" if args.only else "") + f"flujo-{when}-{tag}")
    dir_ = base.with_suffix("")
    dir_.mkdir(parents=True)
    print(f"{len(probs)} problemas · {tag} · contrato {args.modelo_contrato if contratos is None else args.contratos.name}"
          f" · cuerpo {args.modelo_cuerpo} · carga {os.getloadavg()[0]:.2f}", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        filas = list(ex.map(lambda p: run_one(p, dir_, contratos, args.modelo_contrato, args.modelo_cuerpo), probs))
    fc = [c for c, _ in filas if c is not None]
    fb = [b for _, b in filas]
    Path(f"{base}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in fb))
    if fc:
        cb = RESULTADOS / (("humo-" if args.only else "") + f"contratos-mcp-{when}-{args.modelo_contrato}.jsonl")
        cb.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in fc))
    md = resumen(fc, fb, when, tag)
    Path(f"{base}.md").write_text(md)
    print(md)
    print(f"detalle: {base}.jsonl · trazas y almacenes en {dir_.relative_to(ROOT)}/", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
