#!/usr/bin/env bash
# Crea el worktree de una subtarea en paralelo (CLAUDE.md raíz § 5, párrafo "Paralelismo").
#
# Uso: worktree-crear.sh <slug> <T<n>> [rama_base]
#   <slug>       slug del plan, ^[a-z0-9][a-z0-9-]*$
#   <T<n>>       subtarea, ^T[0-9]+[a-z]?$ (p. ej. T5 o T5a)
#   [rama_base]  rama desde la que se crea (por defecto, la rama actual de la raíz)
#
# Crea `worktrees/<slug>-T<n>` con la rama `<slug>-T<n>`, deja en él una junction `venv` que
# apunta al `venv` de la raíz (junction, sin privilegios de administrador) y corre la prueba de
# humo `manage.py check`. La raíz es `git rev-parse --show-toplevel` del directorio actual.
#
# exit 0 → worktree listo y prueba de humo pasada
# exit 2 → uso inválido, argumentos mal formados o no se está dentro de un repo git
# exit 1 → falló git, la junction o la prueba de humo (el worktree queda para inspección)
set -u

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
  echo "uso: worktree-crear.sh <slug> <T<n>> [rama_base]" >&2
  exit 2
fi

slug="$1"
tarea="$2"
rama_base="${3:-}"

if ! printf '%s' "$slug" | grep -Eq '^[a-z0-9][a-z0-9-]*$'; then
  echo "slug inválido: '$slug' (se espera ^[a-z0-9][a-z0-9-]*\$)" >&2
  exit 2
fi
if ! printf '%s' "$tarea" | grep -Eq '^T[0-9]+[a-z]?$'; then
  echo "subtarea inválida: '$tarea' (se espera ^T[0-9]+[a-z]?\$)" >&2
  exit 2
fi

raiz="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "no se está dentro de un repositorio git" >&2
  exit 2
}

if [ -z "$rama_base" ]; then
  rama_base="$(git -C "$raiz" rev-parse --abbrev-ref HEAD)"
fi

nombre="$slug-$tarea"
ruta="$raiz/worktrees/$nombre"

if [ -e "$ruta" ]; then
  echo "ya existe $ruta" >&2
  exit 1
fi

if ! git -C "$raiz" worktree add "$ruta" -b "$nombre" "$rama_base"; then
  echo "falló git worktree add" >&2
  exit 1
fi

# Junction venv -> <raíz>/venv (rutas en formato Windows para cmd).
enlace_win="$(cygpath -w "$ruta/venv")"
destino_win="$(cygpath -w "$raiz/venv")"
# MSYS2_ARG_CONV_EXCL evita que Git Bash convierta "/J" en una ruta.
if ! MSYS2_ARG_CONV_EXCL="*" cmd /c mklink /J "$enlace_win" "$destino_win" >/dev/null; then
  echo "no se pudo crear la junction venv (worktree en $ruta)" >&2
  exit 1
fi

# Prueba de humo dentro del worktree.
if ! (cd "$ruta" && PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check); then
  echo "prueba de humo fallida; el worktree queda en $ruta para inspección" >&2
  exit 1
fi

echo "worktree listo: $ruta (rama $nombre)"
