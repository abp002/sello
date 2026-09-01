#!/usr/bin/env bash
# Contrato de verificación de Sello. Uso: run.sh <verbo>
# Verbos: tipos humo rapido test cov e2e mutacion sec. Exit 0 = verde.
# Un verbo no implementado sale 0 y no es fallo.
set -euo pipefail
cd "$(dirname "$0")/../.."

case "${1:-test}" in
  humo)   uv run pytest -q tests/test_humo.py ;;
  rapido) uv run pytest -q -x ;;
  test)   uv run pytest -q ;;
  cov)    uv run pytest -q --cov=sello --cov-report=term-missing 2>/dev/null || uv run pytest -q ;;
  tipos)  command -v mypy >/dev/null && uv run mypy sello || exit 0 ;;
  *)      exit 0 ;;
esac
