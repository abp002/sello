#!/usr/bin/env bash
# El experimento decisivo (SEL-9), prerregistrado en el vault: 'Sello frente a Python con el
# contrato escrito aparte'. Corre en un worktree fijado al commit del prerregistro: lo que se
# toque en main mientras corre no entra. Cada paso deja un .hecho y, si se corta, la siguiente
# vez sigue por el primero que falte. Uso: bench/medir-sel9.sh <commit>
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
COMMIT="${1:?uso: bench/medir-sel9.sh <commit del prerregistro>}"
BASE="$HOME/.cache/sello-sel9"
D="$BASE/wt"
OUT="$REPO/bench/resultados"
mkdir -p "$BASE"
if [ ! -d "$D" ]; then git -C "$REPO" worktree add --detach "$D" "$COMMIT"; fi
[ -x "$D/.venv/bin/python" ] || (cd "$D" && uv sync --extra dev -q)
[ "$(git -C "$D" rev-parse --short=7 HEAD)" = "${COMMIT:0:7}" ] || { echo "el worktree no está en $COMMIT"; exit 1; }
export SELLO_BATERIA=nuevas

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

for r in a b; do
  paso contratos "sel9-S-$r" bench/contratar.py --tag "sel9-S-$r"
  paso contratos "sel9-A-$r" bench/contratar.py --aviso --tag "sel9-A-$r"
  paso contratos "sel9-P-$r" bench/contratar.py --lang python --tag "sel9-P-$r"
done
for r in a b; do
  for b in S A; do
    paso juez "sel9-$b-$r" bench/harness3.py --model haiku --cond sello_contrato \
      --contratos "$(ultimo contratos "sel9-$b-$r")" --tag "sel9-$b-$r"
  done
  paso juez "sel9-P-$r" bench/harness3.py --model haiku --cond python_contrato \
    --contratos "$(ultimo contratos "sel9-P-$r")" --tag "sel9-P-$r"
done
for r in a b; do
  for b in S A P; do
    cond=sello_contrato; [ "$b" = P ] && cond=python_contrato
    paso mutantes "sel9-$b-$r" bench/mutantes.py "$(ultimo juez "sel9-$b-$r")" --cond "$cond" --workers 4 --tag "sel9-$b-$r"
    paso literales "sel9-$b-$r" bench/literales.py "$(ultimo contratos "sel9-$b-$r")" --tag "sel9-$b-$r"
  done
done
(cd "$REPO" && .venv/bin/python bench/sel9.py)
echo "== fin $(date +%H:%M)"
