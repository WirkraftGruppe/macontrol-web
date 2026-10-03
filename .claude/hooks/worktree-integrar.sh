#!/usr/bin/env bash
# Integra la rama de una subtarea en paralelo y limpia su worktree (CLAUDE.md raíz § 5,
# párrafo "Paralelismo").
#
# Uso: worktree-integrar.sh <slug> <T<n>> <rama_destino> <ruta>...
#   <slug>, <T<n>>  identifican la rama y el worktree `worktrees/<slug>-T<n>`
#   <rama_destino>  rama (con worktree propio, p. ej. la raíz) donde se mergea
#   <ruta>...       prefijos permitidos (al menos uno); todo archivo cambiado fuera de ellos
#                   hace rechazar la integración
#
# Pasos: rechaza si el worktree de la subtarea o el de destino tienen cambios sin commitear;
# muestra cambios.sh --stat; rechaza si hay archivos fuera de los prefijos; merge --no-ff con
# mensaje "T<n>: integra <slug>-T<n>"; makemigrations --check y tests en el destino; quita la
# junction venv con cmd (nunca borra el contenido del venv real), el worktree y la rama.
#
# exit 0 → integrada y limpia
# exit 2 → uso inválido
# exit 1 → rechazada o fallida (si falló antes del merge no se modificó nada)
set -u

if [ "$#" -lt 4 ]; then
  echo "uso: worktree-integrar.sh <slug> <T<n>> <rama_destino> <ruta>..." >&2
  exit 2
fi

slug="$1"
tarea="$2"
destino="$3"
shift 3

if ! printf '%s' "$slug" | grep -Eq '^[a-z0-9][a-z0-9-]*$'; then
  echo "slug inválido: '$slug'" >&2
  exit 2
fi
if ! printf '%s' "$tarea" | grep -Eq '^T[0-9]+[a-z]?$'; then
  echo "subtarea inválida: '$tarea'" >&2
  exit 2
fi

dir_hooks="$(cd "$(dirname "$0")" && pwd)"
raiz="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "no se está dentro de un repositorio git" >&2
  exit 2
}

nombre="$slug-$tarea"
ruta_sub="$raiz/worktrees/$nombre"

if [ ! -d "$ruta_sub" ]; then
  echo "no existe el worktree $ruta_sub" >&2
  exit 1
fi

# Worktree donde está la rama destino.
ruta_dest="$(git -C "$raiz" worktree list --porcelain | awk -v rama="refs/heads/$destino" '
  /^worktree /{ruta=substr($0,10)} $0=="branch " rama {print ruta; exit}')"
if [ -z "$ruta_dest" ]; then
  echo "la rama destino '$destino' no tiene worktree" >&2
  exit 1
fi

# 1. Sin cambios sin commitear en ninguno de los dos.
for wt in "$ruta_sub" "$ruta_dest"; do
  if [ -n "$(git -C "$wt" status --porcelain)" ]; then
    echo "cambios sin commitear en $wt; commitear o descartar antes de integrar" >&2
    exit 1
  fi
done

# 2. Resumen de cambios.
bash "$dir_hooks/cambios.sh" "$raiz" "$destino" --stat

# 3. Alcance: todo archivo cambiado debe caer bajo algún prefijo permitido.
fuera=""
while IFS= read -r archivo; do
  [ -z "$archivo" ] && continue
  dentro=0
  for prefijo in "$@"; do
    case "$archivo" in
      "$prefijo"*) dentro=1 ;;
    esac
  done
  [ "$dentro" -eq 0 ] && fuera="$fuera$archivo"$'\n'
done < <(git -C "$raiz" diff --name-only "$destino...$nombre")
if [ -n "$fuera" ]; then
  echo "archivos fuera de alcance, no se integra:" >&2
  printf '%s' "$fuera" >&2
  exit 1
fi

# 4. Merge en el worktree destino.
if ! git -C "$ruta_dest" merge --no-ff -m "$tarea: integra $nombre" "$nombre"; then
  echo "el merge falló; resolver en $ruta_dest" >&2
  exit 1
fi

# 5. Migraciones y tests en el destino.
export PYTHONIOENCODING=utf-8 DJANGO_ENV=development
if ! (cd "$ruta_dest" && ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run); then
  echo "makemigrations --check falló tras el merge (worktree intacto)" >&2
  exit 1
fi
if ! (cd "$ruta_dest" && ./venv/Scripts/python.exe manage.py test --keepdb); then
  echo "los tests fallaron tras el merge (worktree intacto)" >&2
  exit 1
fi

# 6. Quita la junction (solo el enlace) y luego el worktree.
if [ -e "$ruta_sub/venv" ]; then
  MSYS2_ARG_CONV_EXCL="*" cmd /c rmdir "$(cygpath -w "$ruta_sub/venv")" || {
    echo "no se pudo quitar la junction venv de $ruta_sub" >&2
    exit 1
  }
fi
git -C "$raiz" worktree remove "$ruta_sub" || exit 1

# 7. Borra la rama.
git -C "$raiz" branch -d "$nombre" || exit 1
echo "integrada $nombre en $destino"
