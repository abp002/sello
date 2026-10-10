#!/usr/bin/env bash
# Medición prerregistrada de SEL-2 (nota 'El probador nombra cada función por su hash').
# C = 37e69b8 y T = 5efca37, cada uno en su worktree con su entorno: lo que se toque en main
# mientras corre no entra. Pensado para la cola de noche: cada paso deja un .hecho y, si la
# noche se corta, la siguiente sigue por el primero que falte. Uso: bench/medir-sel2.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
BASE="$HOME/.cache/sello-sel2"
OUT="$REPO/bench/resultados"
mkdir -p "$BASE"

worktree() {  # nombre commit
  local d="$BASE/$1"
  if [ ! -d "$d" ]; then
    git -C "$REPO" worktree add --detach "$d" "$2"
  fi
  [ -x "$d/.venv/bin/python" ] || (cd "$d" && uv sync --extra dev -q)
  # que no se mueva: el commit del worktree tiene que ser el prerregistrado
  [ "$(git -C "$d" rev-parse --short=7 HEAD)" = "$2" ] || { echo "worktree $1 no está en $2"; exit 1; }
}
worktree C 37e69b8
worktree T 5efca37

R="$REPO/bench/resultados"
VERI=(
  "$R/vericoding-2026-09-06-1502-sonnet-muestra50-semilla1.jsonl"
  "$R/vericoding-2026-09-06-1807-haiku-muestra50-semilla1.jsonl"
  "$R/vericoding-2026-09-12-0937-sonnet-nuevas-2026-09-12-muestra50-semilla1.jsonl"
  "$R/vericoding-2026-09-12-1048-haiku-nuevas-2026-09-12-muestra50-semilla1.jsonl"
)
JUEZ=(juez-2026-09-05-0015-haiku juez-2026-09-29-2331-haiku-contrato juez-2026-09-29-2340-sonnet juez-2026-09-29-2341-haiku-contrato)
MUT=(mutantes-2026-09-03-0644 mutantes-2026-09-05-0029 mutantes-2026-09-05-1656 mutantes-2026-09-05-1931
     mutantes-2026-09-29-2329 mutantes-2026-09-29-2339 mutantes-2026-09-29-2353 mutantes-2026-10-01-0035
     mutantes-2026-10-01-0037 mutantes-2026-10-01-1919 mutantes-2026-10-01-1922)
FLUJO=(0021-mcp 0027-control 1906-mcp 1914-control)

paso() {  # etiqueta lado comando...: corre en el worktree del lado y copia lo que deje a main
  local etiqueta="$1" lado="$2"; shift 2
  local marca="$BASE/$etiqueta.hecho"
  [ -f "$marca" ] && { echo "ya: $etiqueta"; return; }
  echo "== $etiqueta ($lado) $(date +%H:%M) carga $(uptime | sed 's/.*averages: //')"
  local d="$BASE/$lado"
  rm -f "$d"/bench/resultados/*-sel2-"$etiqueta".* "$d"/bench/resultados/*-sel2-"$etiqueta"-*.*
  (cd "$d" && env -u VIRTUAL_ENV .venv/bin/python "$@")
  cp "$d"/bench/resultados/*sel2-"$etiqueta"* "$OUT"/
  touch "$marca"
}

for n in 1 2; do
  paso "reprobar-C$n" C bench/vericoding/reprobar.py "${VERI[@]}" --etiqueta "sel2-reprobar-C$n"
  paso "reprobar-T$n" T bench/vericoding/reprobar.py "${VERI[@]}" --etiqueta "sel2-reprobar-T$n"
done
for lado in C T; do
  paso "probador-$lado-principal" "$lado" bench/probador.py \
    --soluciones $(printf "$R/%s.jsonl " "${JUEZ[@]}") --mutantes $(printf "$R/%s.jsonl " "${MUT[@]}") \
    --etiqueta "sel2-probador-$lado-principal"
  for f in "${FLUJO[@]}"; do
    paso "probador-$lado-flujo-$f" "$lado" bench/probador.py --soluciones "$R/flujo-2026-10-01-$f.jsonl" \
      --etiqueta "sel2-probador-$lado-flujo-$f"
  done
done
P=(); for f in "$OUT"/probador-2026-10-05-1936-cand-E-principal.jsonl "$OUT"/probador-2026-10-05-1943-cand-E-flujo-*.jsonl; do P+=("$f"); done
paso "nombres-T" T bench/nombres.py --programas "${P[@]}" --vericoding "${VERI[@]}" --etiqueta "sel2-nombres-T"
echo "== fin $(date +%H:%M)"
