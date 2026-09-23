#!/usr/bin/env bash
# La demo del hito v0.1: un agente de Claude Code sin más herramientas que el MCP de Sello
# lee la spec, reutiliza una función del almacén leyendo solo su contrato, escribe otra y la
# certifica. Uso, desde la raíz del repo:
#
#     demo/correr.sh [modelo]        # por defecto sonnet
#
# Deja en demo/salida/ el almacén, la traza cruda (stream-json) y la transcripción legible.
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
MODELO="${1:-sonnet}"
SALIDA="$RAIZ/demo/salida"
ETIQUETA="$(date +%Y-%m-%d-%H%M)-$MODELO"
ALMACEN="$SALIDA/$ETIQUETA.db"
mkdir -p "$SALIDA"

# Almacén limpio con las funciones de ejemplo: es lo que el agente encuentra al llegar.
uv run --project "$RAIZ" sello add --store "$ALMACEN" "$RAIZ/ejemplos/basicos.sello" > /dev/null

CONFIG="$(mktemp)"
trap 'rm -f "$CONFIG"' EXIT
cat > "$CONFIG" <<JSON
{"mcpServers": {"sello": {"command": "uv",
  "args": ["run", "--project", "$RAIZ", "sello", "mcp", "--store", "$ALMACEN"]}}}
JSON

# Sin herramientas propias (--tools ""), solo este servidor MCP y sin ajustes del usuario:
# lo que el agente sabe de Sello lo sabe por la API.
claude -p "$(cat "$RAIZ/demo/PROMPT.md")" \
  --model "$MODELO" \
  --tools "" \
  --mcp-config "$CONFIG" --strict-mcp-config \
  --allowedTools "mcp__sello" \
  --setting-sources "" \
  --no-session-persistence \
  --output-format stream-json --verbose \
  < /dev/null > "$SALIDA/$ETIQUETA.jsonl"

uv run --project "$RAIZ" python "$RAIZ/demo/transcripcion.py" "$SALIDA/$ETIQUETA.jsonl" \
  > "$SALIDA/$ETIQUETA.md"
echo "$SALIDA/$ETIQUETA.md"
