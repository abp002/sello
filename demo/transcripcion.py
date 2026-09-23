"""De la traza stream-json de `claude -p` a una transcripción en Markdown: lo que dice el
agente, cada llamada a una tool de Sello con sus argumentos y la respuesta, y el coste.

    python demo/transcripcion.py demo/salida/<etiqueta>.jsonl > demo/salida/<etiqueta>.md

Glue sin tests (política de QA del repo).
"""

from __future__ import annotations

import json
import sys

LARGO = 1500  # la spec entera no cabe en una transcripción legible


def recortar(texto: str) -> str:
    return texto if len(texto) <= LARGO else texto[:LARGO] + f"\n… ({len(texto) - LARGO} caracteres más)"


def bloque(texto: str, lenguaje: str = "") -> str:
    return f"```{lenguaje}\n{texto.rstrip()}\n```\n"


def contenido(resultado) -> str:
    if isinstance(resultado, list):
        return "\n".join(p.get("text", "") for p in resultado if isinstance(p, dict))
    return str(resultado)


def main(ruta: str) -> None:
    salida = ["# Demo de Sello por MCP\n"]
    llamadas = 0
    for linea in open(ruta, encoding="utf-8"):
        evento = json.loads(linea)
        tipo = evento.get("type")
        if tipo == "system" and evento.get("subtype") == "init":
            salida.append(f"Modelo: `{evento.get('model')}`. Tools: "
                          + ", ".join(f"`{t}`" for t in evento.get("tools", [])) + "\n")
        elif tipo == "assistant":
            for parte in evento["message"]["content"]:
                if parte["type"] == "text" and parte["text"].strip():
                    salida.append(parte["text"].strip() + "\n")
                elif parte["type"] == "tool_use":
                    llamadas += 1
                    nombre = parte["name"].removeprefix("mcp__sello__")
                    args = parte.get("input") or {}
                    salida.append(f"**→ `{nombre}`**\n")
                    if "source" in args:
                        salida.append(bloque(args["source"], "sello"))
                    elif args:
                        salida.append(bloque(json.dumps(args, ensure_ascii=False)))
        elif tipo == "user":
            for parte in evento["message"]["content"]:
                if isinstance(parte, dict) and parte.get("type") == "tool_result":
                    salida.append("<details><summary>respuesta</summary>\n\n"
                                  + bloque(recortar(contenido(parte.get("content"))), "json")
                                  + "\n</details>\n")
        elif tipo == "result":
            salida.append(f"---\n\n{llamadas} llamadas a Sello, {evento.get('num_turns')} turnos, "
                          f"{evento.get('total_cost_usd', 0):.2f} USD, "
                          f"{evento.get('duration_ms', 0) / 1000:.0f} s.\n")
    print("\n".join(salida))


if __name__ == "__main__":
    main(sys.argv[1])
