#!/usr/bin/env bash
# ¿Aportan los niveles 2 y 3 sobre contratos de Python? (issue #3), prerregistrado en el vault:
# 'Los niveles 2 y 3 frente a CrossHair con el contrato propio'. Corre en un worktree fijado al commit del prerregistro: lo que se
# toque en main mientras corre no entra. Cada paso deja un .hecho y, si se corta, la siguiente
# vez sigue por el primero que falte. Uso: bench/medir-n3.sh <commit>
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
COMMIT="${1:?uso: bench/medir-n3.sh <commit del prerregistro>}"
BASE="$HOME/.cache/sello-n3"
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

# Haiku escribe contrato y cuerpo. S sello · A sello + aviso (sello.unique) · P python_propio ·
# Q python_propio + aviso (CrossHair).
cond_de() { case $1 in S|A) echo sello;; P|Q) echo python_propio;; esac; }
aviso_de() { case $1 in A|Q) echo --aviso;; esac; }
for r in a b; do
  for b in S A P Q; do
    paso juez "n3-$b-$r" bench/harness3.py --model haiku --cond "$(cond_de $b)" $(aviso_de $b) --tag "n3-$b-$r"
  done
done
for r in a b; do
  for b in S A P Q; do
    paso mutantes "n3-$b-$r" bench/mutantes.py "$(ultimo juez "n3-$b-$r")" --cond "$(cond_de $b)" --workers 4 --tag "n3-$b-$r"
    paso literales "n3-$b-$r" bench/literales.py "$(ultimo juez "n3-$b-$r")" --tag "n3-$b-$r"
  done
done
(cd "$REPO" && SELLO_BATERIA=n3 .venv/bin/python bench/n3.py)
echo "== fin $(date +%H:%M)"
