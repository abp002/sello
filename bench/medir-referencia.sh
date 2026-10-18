#!/usr/bin/env bash
# ¿Cierra la guía del helper de referencia los contratos de las tareas definidas por un proceso? (issue #6), prerregistrado en el
# vault: 'Una frase en la spec no basta para que el contrato fije el resultado'. Corre en un worktree fijado al commit del prerregistro: lo que se
# toque en main mientras corre no entra. Cada paso deja un .hecho y, si se corta, la siguiente
# vez sigue por el primero que falte. Uso: bench/medir-referencia.sh <commit>
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
COMMIT="${1:?uso: bench/medir-referencia.sh <commit del prerregistro>}"
BASE="$HOME/.cache/sello-referencia"
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

# U: el brazo T del issue #5 con la spec que guía el helper de referencia. Haiku, contrato propio, sin aviso.
for r in a b; do
  paso juez "n3-U-$r" bench/harness3.py --model haiku --cond sello --tag "n3-U-$r"
done
for r in a b; do
  paso mutantes "n3-U-$r" bench/mutantes.py "$(ultimo juez "n3-U-$r")" --cond sello --workers 4 --tag "n3-U-$r"
  paso literales "n3-U-$r" bench/literales.py "$(ultimo juez "n3-U-$r")" --tag "n3-U-$r"
done
(cd "$REPO" && SELLO_BATERIA=n3 .venv/bin/python bench/referencia.py)
echo "== fin $(date +%H:%M)"
