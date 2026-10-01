#!/usr/bin/env bash
# Diff consolidado de todos los worktrees de un repo, para revisar antes de integrar en paralelo
# (CLAUDE.md raíz § 5, párrafo "Paralelismo": antes de integrar se revisa esta salida, no los
# informes de los implementadores).
#
# Uso: cambios.sh <repo> [rama_base] [--stat]
#   <repo>       directorio del repositorio git a inspeccionar (. | backend | mobile)
#   [rama_base]  rama contra la que se compara cada worktree (por defecto "main")
#   [--stat]     solo el resumen (--stat); sin esta opción también se imprime el diff completo
#
# Recorre `git worktree list --porcelain` del repo. Para cada worktree muestra: la ruta, la
# rama, el diff contra <rama_base> (commiteado) y lo que hay sin commitear (status --porcelain
# más su propio diff --stat). Si el repo tiene un solo worktree (el principal, sin subtareas en
# paralelo) lo muestra igual y sale con 0: no es un error, solo no hay nada que consolidar.
#
# Solo lectura: no hace `git worktree prune`, `fetch` ni ningún comando que escriba en el repo.
#
# exit 0 → se pudo listar y comparar contra <rama_base>
# exit 2 → uso inválido, <repo> no es un repositorio git o <rama_base> no existe
set -u

solo_stat=0
rama_base=""
repo=""
posicion=0

if [ "$#" -lt 1 ] || [ -z "${1:-}" ]; then
  echo "uso: cambios.sh <repo> [rama_base] [--stat]" >&2
  exit 2
fi

repo="$1"
shift

for arg in "$@"; do
  case "$arg" in
    --stat)
      solo_stat=1
      ;;
    -*)
      echo "uso: opción desconocida '$arg' (solo se acepta --stat)" >&2
      exit 2
      ;;
    *)
      posicion=$((posicion + 1))
      if [ "$posicion" -gt 1 ]; then
        echo "uso: cambios.sh <repo> [rama_base] [--stat]" >&2
        exit 2
      fi
      rama_base="$arg"
      ;;
  esac
done

if [ -z "$rama_base" ]; then
  rama_base="main"
fi

if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "'$repo' no es un repositorio git" >&2
  exit 2
fi

if ! git -C "$repo" rev-parse --verify --quiet "${rama_base}^{commit}" >/dev/null; then
  echo "no existe la rama base '$rama_base' en '$repo'" >&2
  exit 2
fi

# Procesa un worktree: ruta y rama en $1 y $2, ya resueltos por el llamador.
mostrar_worktree() {
  wt_ruta="$1"
  wt_rama="$2"

  echo "=== worktree: $wt_ruta (rama: $wt_rama) ==="

  echo "-- diff --stat contra $rama_base ($rama_base...HEAD) --"
  git -C "$wt_ruta" diff --stat "${rama_base}...HEAD" 2>&1

  if [ "$solo_stat" -eq 0 ]; then
    echo "-- diff completo contra $rama_base --"
    git -C "$wt_ruta" diff "${rama_base}...HEAD" 2>&1
  fi

  echo "-- sin commitear (git status --porcelain) --"
  estado="$(git -C "$wt_ruta" status --porcelain 2>&1)"
  if [ -n "$estado" ]; then
    printf '%s\n' "$estado"
  else
    echo "  (nada sin commitear)"
  fi

  echo "-- diff --stat de lo sin commitear (contra HEAD) --"
  git -C "$wt_ruta" diff --stat HEAD 2>&1

  if [ "$solo_stat" -eq 0 ]; then
    echo "-- diff completo de lo sin commitear (contra HEAD) --"
    git -C "$wt_ruta" diff HEAD 2>&1
  fi

  echo ""
}

listado="$(git -C "$repo" worktree list --porcelain)"

wt_ruta=""
wt_rama=""
hay_worktree=0

procesar_linea() {
  case "$1" in
    "worktree "*)
      wt_ruta="${1#worktree }"
      wt_rama="(detached)"
      ;;
    "branch "*)
      wt_rama="${1#branch }"
      wt_rama="${wt_rama#refs/heads/}"
      ;;
    "detached")
      wt_rama="(detached)"
      ;;
    "")
      if [ -n "$wt_ruta" ]; then
        mostrar_worktree "$wt_ruta" "$wt_rama"
        hay_worktree=1
        wt_ruta=""
        wt_rama=""
      fi
      ;;
  esac
}

while IFS= read -r linea; do
  procesar_linea "$linea"
done <<EOF
$listado
EOF

# `git worktree list --porcelain` no siempre termina con línea en blanco: se procesa el último
# bloque si quedó pendiente.
if [ -n "$wt_ruta" ]; then
  mostrar_worktree "$wt_ruta" "$wt_rama"
  hay_worktree=1
fi

if [ "$hay_worktree" -eq 0 ]; then
  echo "no se encontró ningún worktree en '$repo'" >&2
  exit 2
fi

exit 0
