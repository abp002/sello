#!/usr/bin/env python3
"""Tercera medición: el juez imperfecto. Cuánto error llega a producción.

El bucle de generación solo ve el juez débil: compilador + los dos ejemplos visibles del
enunciado. Cuando acepta, la solución pasa al oráculo (referencia + casos generados,
`bench/ambiguos/`), que cuenta silenciosos, rechazados y cazados por zona. Diseño y
prerregistración en el vault: 'El juez imperfecto mide lo que llega a producción'.

Condiciones: sello · python · python_asserts (Python con la instrucción de poner asserts).
Aparte, `python_propio` (issue #3): la gemela en Python de `sello`, con el contrato en el docstring
escrito por el mismo modelo, comprobado en cada llamada y con CrossHair en el juez débil. Con
`--aviso`, si el contrato aceptado admite dos respuestas, una vuelta más con el testigo.
Aparte, `sello_contrato`: el contrato lo escribió otro (se toma de una corrida anterior con
`--contratos`, ver `contrato.py`) y el modelo solo escribe el cuerpo. No entra en `all`. Su
gemela en Python, `python_contrato` (SEL-16): el contrato en el docstring (`pre:`/`post:`), que
se comprueba en cada llamada, y CrossHair en el juez débil como el probador (`contrato_py.py`).

La batería es `ambiguos/`; con SELLO_BATERIA=nuevas, la del experimento decisivo (SEL-9).

    uv run python bench/harness3.py --model haiku
    uv run python bench/harness3.py --model haiku --only nth --cond sello   # humo
    uv run python bench/harness3.py --model haiku --cond sello_contrato \
        --contratos bench/resultados/juez-2026-09-05-0015-sonnet.jsonl
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import RESULTADOS, ROOT, SPEC, ask, extract, py_val, sello_lit  # noqa: E402
import contrato as ct  # noqa: E402
import contrato_py as cp  # noqa: E402
import juez  # noqa: E402

AQUI = Path(__file__).resolve().parent
BATERIA = os.environ.get("SELLO_BATERIA", "ambiguos")
PROBLEMAS = AQUI / BATERIA
CONDS = ["sello", "python", "python_asserts"]
CONTRATO = "sello_contrato"
PY_CONTRATO = "python_contrato"
PY_PROPIO = "python_propio"  # issue #3: el contrato de Python lo escribe el mismo modelo que el cuerpo
CONDS_TODAS = CONDS + [CONTRATO, PY_CONTRATO, PY_PROPIO]
PY_CONTRATOS = (PY_CONTRATO, PY_PROPIO)  # contratos comprobados en cada llamada y CrossHair en el juez débil

# La guía de contratos de la spec de Sello, dicha para Python (la misma que `contratar.prompt_py`).
GUIA_PY = ("The conditions are checked on every call, and a tool searches for inputs that break them. "
           "Preconditions state everything the task lets you assume about the arguments (a value is "
           "unique, the list has no repeats, `k` is within bounds); whatever is not in them the body must "
           "handle. Postconditions must reject wrong results: a condition that every return value "
           "satisfies certifies nothing, and a bound alone (`__return__ >= 1`, `__return__ <= len(xs)`) "
           "does not reject a wrong value inside the bound. State what the result contains or how it "
           "relates to the arguments. ")


def es_sello(cond: str) -> bool:
    return cond.startswith("sello")


# ---------- prompts ----------

def llamada(p: dict, args: list) -> str:
    return f"{p['fn']}(" + ", ".join(sello_lit(a) for a in args) + ")"


def ejemplos(p: dict, lang: str) -> str:
    out = []
    for c in p["visible"]:
        if lang == "sello":
            out.append(f"{llamada(p, c['args'])} == {sello_lit(c['expect'])}")
        else:
            args = ", ".join(repr(py_val(a)) for a in c["args"])
            out.append(f"{p['fn']}({args}) == {py_val(c['expect'])!r}")
    return "For example: " + "; ".join(out) + "."


def prompt(p: dict, cond: str, prev: tuple[str, str] | None, contrato=None) -> str:
    if cond == PY_PROPIO:
        head = (f"Task: write a Python function `{p['python']}`. {p['statement']} {ejemplos(p, 'python')}\n"
                f"Give `{p['fn']}` a docstring that holds its contract in the format CrossHair reads: one "
                f"line `pre: <boolean expression on the arguments>` per precondition and one line "
                f"`post: <boolean expression>` per postcondition, where `__return__` is the returned "
                f"value; at least one `post:`. {GUIA_PY}Any helper function your conditions call must be "
                f"complete. No imports, no input/output, no prints. You may add helper functions. Tests "
                f"will call `{p['fn']}`.\n"
                f"Reply with one ```python block containing the whole code.")
        fence, tail = "python", "the whole corrected code"
    elif cond == PY_CONTRATO:
        assert contrato is not None
        head = (f"Task: complete the Python code below so that it defines `{p['python']}`. {p['statement']} "
                f"{ejemplos(p, 'python')}\n"
                f"The contract is fixed and was written by someone else: the signature and the docstring "
                f"of `{p['fn']}` (its `pre:` and `post:` conditions, checked on every call; `__return__` "
                f"is the returned value), and the helper functions shown, must appear unchanged in your "
                f"code. Write the body of `{p['fn']}` in place of `...`. You may add helper functions of "
                f"your own. No imports, no input/output, no prints. A tool searches for inputs that break "
                f"the conditions. Tests will call `{p['fn']}`.\n\n```python\n{contrato.texto}\n```\n\n"
                f"Reply with one ```python block containing the whole code.")
        fence, tail = "python", "the whole corrected code"
    elif cond == CONTRATO:
        assert contrato is not None
        head = (f"Below is the complete specification of Sello, a small programming language.\n\n"
                f"{SPEC}\n\n---\n\n"
                f"Task: complete the Sello program below so that it defines `{p['sello']}`. {p['statement']} "
                f"{ejemplos(p, 'sello')}\n"
                f"The contract is fixed and was written by someone else: the signature, `requires`, "
                f"`ensures`, `effects` and `example` lines of `{p['fn']}`, and the helper functions "
                f"shown, must appear unchanged in your program. Write the body of `{p['fn']}`. You may "
                f"add helper functions of your own; every function needs its contract clauses. "
                f"Tests will call `{p['fn']}`.\n\n```sello\n{contrato.texto}\n```\n\n"
                f"Reply with one ```sello block containing the whole program.")
        fence, tail = "sello", "the whole corrected program"
    elif cond == "sello":
        head = (f"Below is the complete specification of Sello, a small programming language.\n\n"
                f"{SPEC}\n\n---\n\n"
                f"Task: write a Sello program that defines `{p['sello']}`. {p['statement']} "
                f"{ejemplos(p, 'sello')}\n"
                f"You may add helper functions. Every function needs its contract clauses. "
                f"Tests will call `{p['fn']}`.\n"
                f"Reply with one ```sello block containing the whole program.")
        fence, tail = "sello", "the whole corrected program"
    else:
        extra = ""
        if cond == "python_asserts":
            extra = ("Use `assert` to check every precondition on the arguments at the start of "
                     "the function, and `assert` every property the result must satisfy before "
                     "returning it. ")
        head = (f"Task: write a Python function `{p['python']}`. {p['statement']} "
                f"{ejemplos(p, 'python')}\n"
                f"{extra}No imports, no input/output, no prints. You may add helper functions. "
                f"Tests will call `{p['fn']}`.\n"
                f"Reply with one ```python block containing the whole code.")
        fence, tail = "python", "the whole corrected code"
    if prev is None:
        return head
    code, err = prev
    return (f"{head}\n\nYour previous code:\n```{fence}\n{code}\n```\n\nIt was rejected:\n"
            f"```\n{err}\n```\n\nFix it and reply with {tail} in one ```{fence} block.")


# ---------- ejecución caso a caso ----------

def casos_sello(p: dict, casos: list[dict]) -> str:
    return json.dumps([{"call": llamada(p, c["args"]), "expect": sello_lit(c["expect"])} for c in casos])


def ejecutar_sello(code: str, p: dict, casos: list[dict], timeout: int = 60,
                   prover: bool = True) -> list[dict] | dict:
    """Corre `sello test`. Devuelve la lista de casos con `result` bruto, o el error de compilación.
    Sin `prover`, la carga no pasa el probador (`--no-prover`): el programa se juzga en ejecución,
    con sus contratos."""
    with tempfile.TemporaryDirectory() as d:
        src = Path(d, "sol.sello"); src.write_text(code + "\n")
        cj = Path(d, "cases.json"); cj.write_text(casos_sello(p, casos))
        try:
            r = subprocess.run([sys.executable, "-m", "sello.cli", "test", str(src), str(cj),
                                "--case-seconds", str(CASO_S)] + ([] if prover else ["--no-prover"]),
                               capture_output=True, text=True, timeout=timeout, cwd=ROOT)
        except subprocess.TimeoutExpired:
            return {"error": {"code": "E500", "what": f"timeout after {timeout}s"}, "timeout": True}
    out = r.stdout.strip() or r.stderr.strip()[-1500:]
    try:
        d = json.loads(out)
    except json.JSONDecodeError:
        return {"error": {"code": "E000", "what": out[-800:]}}
    if "error" in d:
        return d
    fallos = {f["call"]: f for f in d.get("failed", [])}
    return [{**c, "call": llamada(p, c["args"]), "result": juez.resultado_sello(fallos.get(llamada(p, c["args"]))),
             "detail": fallos.get(llamada(p, c["args"]))} for c in casos]


CASO_S = 3  # tope por caso del oráculo, el mismo en Sello y en Python (issue #2)

DRIVER = r'''
import json, signal, sys, traceback
code, cases, fn = sys.argv[1], json.loads(sys.argv[2]), sys.argv[3]
ns = {}
try:
    exec(open(code).read(), ns)
    if sys.argv[4]:  # contratos activos: el nivel 1 de Python (contrato_py.ENFORCE)
        exec(sys.argv[4], ns)
        ns["_contratar"](ns)
    f = ns[fn]
except Exception:
    print(json.dumps({"error": traceback.format_exc(limit=2)[-1200:]})); sys.exit(1)
class Timeout(Exception): pass
def alarm(*_): raise Timeout()
signal.signal(signal.SIGALRM, alarm)
out = []
for c in cases:
    signal.alarm(int(sys.argv[5]))
    try:
        got = f(*c["args"])
        exp = c["expect"]
        ok = got == exp and isinstance(got, bool) == isinstance(exp, bool)
        out.append({"status": "ok" if ok else "wrong", "got": repr(got)})
    except AssertionError as e:
        out.append({"status": "assert", "got": f"AssertionError: {e}"})
    except Timeout:
        out.append({"status": "timeout", "got": "timeout"})
    except BaseException as e:
        out.append({"status": "raise", "got": f"{type(e).__name__}: {e}"[:200]})
    finally:
        signal.alarm(0)
print(json.dumps(out))
'''


def ejecutar_python(code: str, p: dict, casos: list[dict], timeout: int = 60,
                    contratos: bool = False) -> list[dict] | dict:
    """Con `contratos`, cada `pre:`/`post:` de un docstring se comprueba en cada llamada: un `post`
    violado es cazado (AssertionError) y un `pre` violado, rechazo."""
    with tempfile.TemporaryDirectory() as d:
        src = Path(d, "sol.py"); src.write_text(code + "\n")
        drv = Path(d, "driver.py"); drv.write_text(DRIVER)
        cj = json.dumps([{"args": [py_val(a) for a in c["args"]], "expect": py_val(c["expect"])} for c in casos])
        try:
            r = subprocess.run([sys.executable, str(drv), str(src), cj, p["fn"], cp.ENFORCE if contratos else "", str(CASO_S)],
                               capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"error": f"timeout after {timeout}s"}
    try:
        d = json.loads(r.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return {"error": (r.stdout + r.stderr)[-1200:]}
    if isinstance(d, dict):
        return d
    return [{**c, "call": llamada(p, c["args"]), "result": juez.resultado_python(x["status"]), "detail": x}
            for c, x in zip(casos, d)]


def ejecutar(cond: str, code: str, p: dict, casos: list[dict], timeout: int = 60) -> list[dict] | dict:
    if cond in PY_CONTRATOS:
        return ejecutar_python(code, p, casos, timeout, contratos=True)
    return (ejecutar_sello if es_sello(cond) else ejecutar_python)(code, p, casos, timeout)


# ---------- juez débil ----------

def _sin_post(code: str, fn: str) -> str | None:
    """En `python_propio`, el contrato es obligatorio como en Sello: al menos un `post:`."""
    import ast
    try:
        main = next((n for n in ast.parse(code).body if isinstance(n, ast.FunctionDef) and n.name == fn), None)
    except SyntaxError:
        return None  # lo dice la ejecución
    if main is not None and not cp.condiciones(ast.get_docstring(main))[1]:
        return f"`{fn}` needs its contract: at least one `post:` line in its docstring."
    return None


def aviso_de(cond: str, code: str, fn: str) -> str | None:
    """El aviso de ambigüedad del contrato de una solución aceptada (issue #3): el de `contratar`,
    con `sello.unique` en Sello y CrossHair en Python."""
    import contratar
    return (contratar.aviso_py if cond in PY_CONTRATOS else contratar.aviso)(code, fn)


def juez_debil(cond: str, code: str, p: dict, contrato=None) -> tuple[bool, str, str]:
    """(aceptado, feedback, fase). Compila y pasa los ejemplos visibles. Con contrato
    congelado, antes de nada comprueba que el programa lo respeta (fase `contract`). En
    `python_contrato`, tras los ejemplos, CrossHair (fase `prover`): en Sello el probador va dentro
    del compilador."""
    if contrato is not None:
        v = (cp.violacion if cond == PY_CONTRATO else ct.violacion)(contrato, code)
        if v:
            return False, v, "contract"
    if cond == PY_PROPIO:
        v = _sin_post(code, p["fn"])
        if v:
            return False, v, "contract"
    r = ejecutar(cond, code, p, p["visible"])
    if isinstance(r, dict):
        return False, json.dumps(r, ensure_ascii=False), "compile"
    fallos = [x for x in r if x["result"] != juez.OK]
    if not fallos and cond in PY_CONTRATOS:
        cx = cp.crosshair(code)
        if cx:
            return False, cx, "prover"
    if not fallos:
        return True, "", "ok"
    if es_sello(cond):
        fb = json.dumps({"ok": False, "failed": [x["detail"] for x in fallos]}, ensure_ascii=False)
    else:
        fb = "\n".join(f"{x['call']}: expected {py_val(x['expect'])!r}, got {x['detail']['got']}" for x in fallos)
    return False, fb, "tests"


# ---------- una corrida ----------

def run_one(p: dict, cond: str, model: str, max_attempts: int, contratos: dict | None = None,
            aviso: bool = False) -> dict:
    prev: tuple[str, str] | None = None
    attempts: list[dict] = []
    accepted_at: int | None = None
    code = ""
    contrato = None
    if cond in (CONTRATO, PY_CONTRATO):
        if p["fn"] not in contratos:  # un contrato a ciegas que no compila: el problema no se corre
            print(f"  {p['fn']:<15} {cond:<15} sin contrato: no se corre", file=sys.stderr, flush=True)
            return {"problem": p["fn"], "cond": cond, "model": model, "accepted_at": None, "contrato": None,
                    "sin_contrato": True, "attempts": 0, "cost": 0.0, "tokens_in": 0, "tokens_out": 0,
                    "thinking": 0, "ms": 0, "code": None, "oracle": {}, "oracle_cases": [], "detail": []}
        origen = contratos[p["fn"]]
        contrato = (cp.extraer if cond == PY_CONTRATO else ct.extraer)(origen["code"], p["fn"])
    for i in range(1, max_attempts + 1):
        a = ask(prompt(p, cond, prev, contrato), model)
        code = extract(a["text"], "sello" if es_sello(cond) else "python")
        ok, feedback, phase = juez_debil(cond, code, p, contrato)
        m = re.search(r'"code":\s*"(E\d{3})"', feedback) if (es_sello(cond) and not ok) else None
        attempts.append({"n": i, "ok": ok, "phase": phase, "sello_error": m.group(1) if m else None,
                         "cost": a["cost"], "tokens_in": a["tokens_in"], "tokens_out": a["tokens_out"],
                         "thinking": a.get("thinking", 0), "ms": a["ms"], "models": a.get("models"),
                         "code": code, "feedback": feedback[:2000]})
        print(f"  {p['fn']:<15} {cond:<15} intento {i}: {'aceptado' if ok else phase + (' ' + m.group(1) if m else '')}",
              file=sys.stderr, flush=True)
        if ok:
            accepted_at = i
            break
        prev = (code, feedback)

    # El aviso (issue #3): si el contrato aceptado admite dos respuestas, una sola vuelta más con el
    # testigo. No es un rechazo: si lo que vuelve no pasa el juez débil, queda lo ya aceptado.
    avisado: list[str] = []
    sustituye = None
    if aviso and accepted_at:
        msg = aviso_de(cond, code, p["fn"])
        if msg:
            avisado.append(msg)
            a = ask(prompt(p, cond, (code, msg), contrato), model)
            nuevo = extract(a["text"], "sello" if es_sello(cond) else "python")
            ok, feedback, phase = juez_debil(cond, nuevo, p, contrato)
            attempts.append({"n": len(attempts) + 1, "ok": ok, "phase": "ambiguous" if ok else phase,
                             "sello_error": None, "cost": a["cost"], "tokens_in": a["tokens_in"],
                             "tokens_out": a["tokens_out"], "thinking": a.get("thinking", 0), "ms": a["ms"],
                             "models": a.get("models"), "code": nuevo, "feedback": (msg + "\n" + feedback)[:2000]})
            sustituye = ok
            if ok:
                code = nuevo
            print(f"  {p['fn']:<15} {cond:<15} aviso: {'sustituye' if ok else 'queda lo aceptado (' + phase + ')'}",
                  file=sys.stderr, flush=True)

    oracle_cases: list[dict] = []
    oracle: dict = {}
    if accepted_at:
        r = ejecutar(cond, code, p, p["oracle"])
        if isinstance(r, dict):
            oracle_cases = [{**c, "result": juez.REJECT, "detail": r} for c in p["oracle"]]
        else:
            oracle_cases = r
        oracle = juez.contar(oracle_cases)
        print(f"  {p['fn']:<15} {cond:<15} oráculo: silenciosos {oracle['silenciosos']} "
              f"(dom {oracle['dom_silencioso']}, amb {oracle['amb_silencioso']}) · ruidosos dom {oracle['dom_ruidoso']} "
              f"· declarados amb {oracle['amb_declarado']} · cazados {oracle['cazados']}", file=sys.stderr, flush=True)

    info_contrato = None
    if contrato is not None:
        info_contrato = {"de": origen["model"], "origen": origen["origen"], "principal": p["fn"],
                         "fns": contrato.nombres, "texto": contrato.texto,
                         "rechazos": sum(x["phase"] == "contract" for x in attempts)}
    return {"problem": p["fn"], "cond": cond, "model": model, "accepted_at": accepted_at,
            "contrato": info_contrato, "aviso": aviso, "avisado": avisado, "aviso_sustituye": sustituye,
            "attempts": len(attempts), "cost": sum(x["cost"] for x in attempts),
            "tokens_in": sum(x["tokens_in"] for x in attempts),
            "tokens_out": sum(x["tokens_out"] for x in attempts),
            "thinking": sum(x["thinking"] for x in attempts),
            "ms": sum(x["ms"] for x in attempts), "code": code if accepted_at else None,
            "oracle": oracle, "oracle_cases": [{k: v for k, v in c.items() if k != "expect"} | {"expect": c["expect"]}
                                              for c in oracle_cases],
            "detail": attempts}


def cargar_contratos(path: Path) -> dict[str, dict]:
    """Soluciones `sello` aceptadas de una corrida del juez, por problema. Los contratos se
    extraen de ellas (`contrato.extraer`); el modelo que las escribió queda anotado. De una
    corrida de `contratar.py`, los contratos a ciegas que compilan, aceptados o no por su juez
    débil (regla 1 de 'El contrato se puede escribir sin el cuerpo')."""
    out: dict[str, dict] = {}
    for line in path.read_text().splitlines():
        r = json.loads(line)
        if (r["cond"] in ("sello", PY_PROPIO) and r.get("code") and r.get("accepted_at")) or \
                (r["cond"] in ("contrato", "contrato_py") and r.get("compila")):
            out[r["problem"]] = {"code": r["code"], "model": r["model"], "origen": path.name}
    return out


def de_contratar(path: Path) -> bool:
    return any(json.loads(line)["cond"] in ("contrato", "contrato_py") for line in path.read_text().splitlines())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--cond", choices=CONDS_TODAS + ["all"], default="all")
    ap.add_argument("--contratos", type=Path,
                    help=f"corrida del juez (jsonl) de la que tomar los contratos; obligatorio con --cond {CONTRATO}")
    ap.add_argument("--only", help="nombre de un problema")
    ap.add_argument("--attempts", type=int, default=5)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--tag", default="", help="sufijo del nombre de la corrida")
    ap.add_argument("--aviso", action="store_true",
                    help="issue #3: si el contrato aceptado admite dos respuestas, una vuelta más con el testigo")
    args = ap.parse_args()

    probs = [json.loads(f.read_text()) for f in sorted(PROBLEMAS.glob("*.json"))]
    if args.only:
        probs = [p for p in probs if p["fn"] == args.only]
    conds = CONDS if args.cond == "all" else [args.cond]
    contratos = None
    if CONTRATO in conds or PY_CONTRATO in conds:
        if not args.contratos:
            ap.error(f"--cond {conds[0]} necesita --contratos")
        contratos = cargar_contratos(args.contratos)
        faltan = [p["fn"] for p in probs if p["fn"] not in contratos]
        if faltan and not de_contratar(args.contratos):  # los de contratar.py sin contrato no se corren
            ap.error(f"{args.contratos.name} no tiene solución `sello` aceptada para: {', '.join(faltan)}")
    jobs = [(p, c) for p in probs for c in conds]
    when = dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    print(f"{len(jobs)} corridas, modelo {args.model}, hasta {args.attempts} intentos", file=sys.stderr)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        rows = list(ex.map(lambda j: run_one(j[0], j[1], args.model, args.attempts, contratos, args.aviso), jobs))

    RESULTADOS.mkdir(exist_ok=True)
    tag = f"juez-{when}-{args.model}" + ("-contrato" if conds == [CONTRATO] else "") \
        + ("-contrato-py" if conds == [PY_CONTRATO] else "") + ("-propio-py" if conds == [PY_PROPIO] else "") \
        + ("-nuevas" if BATERIA == "nuevas" else "") + ("-aviso" if args.aviso else "")
    if contratos is not None and de_contratar(args.contratos):
        tag += "-ciegas"
    tag += f"-{args.tag}" if args.tag else ""
    base = RESULTADOS / (tag if not args.only else f"humo-{tag}")
    with open(base.with_suffix(".jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    md = juez.resumen(rows, args.model, when)
    base.with_suffix(".md").write_text(md)
    print(md)
    print(f"detalle: {base.with_suffix('.jsonl')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
