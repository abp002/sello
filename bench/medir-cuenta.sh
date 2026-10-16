#!/usr/bin/env bash
# ¿Cierran `count` y `sum` con condición los contratos de cotas? (issue #5), prerregistrado en el
# vault: 'Contar y sumar con condición cierra los contratos de cotas'. Corre en un worktree fijado al commit del prerregistro: lo que se
# toque en main mientras corre no entra. Cada paso deja un .hecho y, si se corta, la siguiente
# vez sigue por el primero que falte. Uso: bench/medir-cuenta.sh <commit>
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
COMMIT="${1:?uso: bench/medir-cuenta.sh <commit del prerregistro>}"
BASE="$HOME/.cache/sello-cuenta"
D="$BASE/wt"
OUT="$REPO/bench/resultados"
mkdir -p "$BASE"
if [ ! -d "$D" ]; then git -C "$REPO" worktree add --detach "$D" "$COMMIT"; fi
[ -x "$D/.venv/bin/python" ] || (cd "$D" && uv sync --extra dev -q)
[ "$(git -C "$D" rev-parse --short=7 HEAD)" = "${COMMIT:0:7}" ] || { echo "el worktree no está en $COMMIT"; exit 1; }
export SELLO_BATERIA=n3

paso() {  # prefijo etiqueta comando...: corre en el worktree y copia a main SOLO <prefijo>-*-<etiqueta>.*
  local pre="$1" et="$2"; shift 2
  local marca="$BASE/$pre-$et.hecho"
  [ -f "$marca" ] && { echo "ya: $pre $et"; return; }
  echo "== $pre $et $(date +%H:%M) carga $(uptime | sed 's/.*averages: //')"
  rm -f "$D"/bench/resultados/"$pre"-*-"$et".*  # solo lo de este paso: los demás comparten etiqueta
  (cd "$D" && env -u VIRTUAL_ENV -u CLAUDE_CONFIG_DIR .venv/bin/python "$@")
  cp "$D"/bench/resultados/"$pre"-*-"$et".* "$OUT"/
  touch "$marca"
}
ultimo() { ls -t "$D"/bench/resultados/"$1"-*-"$2".jsonl | head -1; }

# T (S′): el brazo S del issue #3 con la spec que trae `count` y `sum`. Haiku, contrato propio, sin aviso.
for r in a b; do
  paso juez "n3-T-$r" bench/harness3.py --model haiku --cond sello --tag "n3-T-$r"
done
for r in a b; do
  paso mutantes "n3-T-$r" bench/mutantes.py "$(ultimo juez "n3-T-$r")" --cond sello --workers 4 --tag "n3-T-$r"
  paso literales "n3-T-$r" bench/literales.py "$(ultimo juez "n3-T-$r")" --tag "n3-T-$r"
done
(cd "$REPO" && SELLO_BATERIA=n3 .venv/bin/python bench/cuenta.py)
echo "== fin $(date +%H:%M)"
