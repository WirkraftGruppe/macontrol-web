#!/usr/bin/env bash
# Presupuesto de líneas agregadas por subtarea, medido contra el commit base de un plan.
#
# Uso: presupuesto.sh <repo> <base> <max> [rutas...]
#   <repo>  directorio del repositorio git a inspeccionar (. | backend | mobile)
#   <base>  commit contra el que se mide el diff (normalmente commit_base del plan)
#   <max>   máximo de líneas agregadas permitido (entero >= 0)
#   [rutas] opcional: limita el conteo a esas rutas, relativas a <repo>
#
# Cuenta las líneas agregadas desde <base> hasta el árbol de trabajo (incluye lo que no está
# commiteado): el diff de los archivos ya versionados (`git diff --numstat <base>`) más el
# contenido íntegro de los archivos nuevos sin rastrear (`git ls-files --others
# --exclude-standard`). Los binarios (numstat los marca con "-") no suman líneas pero se listan
# igual. El presupuesto se fija antes de empezar la subtarea y nunca se sube durante ella
# (CLAUDE.md raíz § "El plan lleva criterios comprobables por máquina"): si el trabajo no entra,
# se parte en subtareas más chicas.
#
# exit 0 → total <= max
# exit 1 → total > max (se imprime el detalle igual, para que se vea qué archivo lo explica)
# exit 2 → uso inválido, <repo> no es un repositorio git o <base> no existe
set -u

if [ "$#" -lt 3 ] || [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
  echo "uso: presupuesto.sh <repo> <base> <max> [rutas...]" >&2
  exit 2
fi

repo="$1"
base="$2"
max="$3"
shift 3
rutas=("$@")

# <max> debe ser un entero no negativo: cualquier otra cosa es un error de uso, no de presupuesto.
case "$max" in
  '' | *[!0-9]*)
    echo "uso inválido: <max> debe ser un entero >= 0 (se recibió '$max')" >&2
    exit 2
    ;;
esac

if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "'$repo' no es un repositorio git" >&2
  exit 2
fi

if ! git -C "$repo" rev-parse --verify --quiet "${base}^{commit}" >/dev/null; then
  echo "no existe el commit base '$base' en '$repo'" >&2
  exit 2
fi

# Cuenta las líneas de un archivo tal como quedan en disco. `wc -l` cuenta saltos de línea, así
# que una última línea sin "\n" final queda afuera: se detecta y se suma aparte.
contar_lineas() {
  archivo="$1"
  lineas="$(wc -l <"$archivo" | tr -d '[:space:]')"
  if [ -s "$archivo" ] && [ -n "$(tail -c1 -- "$archivo")" ]; then
    lineas=$((lineas + 1))
  fi
  printf '%s' "$lineas"
}

tab="$(printf '\t')"
detalle="$(mktemp)"
trap 'rm -f "$detalle"' EXIT

# Archivos ya versionados: diff --numstat da "<agregadas>\t<borradas>\t<archivo>".
if [ "${#rutas[@]}" -gt 0 ]; then
  numstat="$(git -C "$repo" diff --numstat "$base" -- "${rutas[@]}")"
else
  numstat="$(git -C "$repo" diff --numstat "$base")"
fi

if [ -n "$numstat" ]; then
  while IFS="$tab" read -r agregadas _borradas archivo; do
    if [ "$agregadas" = "-" ]; then
      printf '0\tbinario\t%s\n' "$archivo" >>"$detalle"
    else
      printf '%s\t%s\t%s\n' "$agregadas" "$agregadas" "$archivo" >>"$detalle"
    fi
  done <<EOF
$numstat
EOF
fi

# Archivos nuevos sin rastrear: cuentan enteros como líneas agregadas.
if [ "${#rutas[@]}" -gt 0 ]; then
  sin_rastrear="$(git -C "$repo" ls-files --others --exclude-standard -- "${rutas[@]}")"
else
  sin_rastrear="$(git -C "$repo" ls-files --others --exclude-standard)"
fi

if [ -n "$sin_rastrear" ]; then
  while IFS= read -r archivo; do
    ruta_absoluta="$repo/$archivo"
    if [ -f "$ruta_absoluta" ]; then
      lineas="$(contar_lineas "$ruta_absoluta")"
      printf '%s\t%s\t%s\n' "$lineas" "$lineas" "$archivo" >>"$detalle"
    fi
  done <<EOF
$sin_rastrear
EOF
fi

total=0
if [ -s "$detalle" ]; then
  while IFS="$tab" read -r orden _mostrar _archivo; do
    total=$((total + orden))
  done <"$detalle"
fi

echo "total de líneas agregadas: $total (máximo: $max)"
echo "top 10 por líneas agregadas:"
if [ -s "$detalle" ]; then
  sort -t "$tab" -k1,1nr -- "$detalle" | head -10 | while IFS="$tab" read -r _orden mostrar archivo; do
    printf '  %s\t%s\n' "$mostrar" "$archivo"
  done
else
  echo "  (sin cambios en las rutas indicadas)"
fi

if [ "$total" -gt "$max" ]; then
  echo "No recortar comentarios, docs, tests ni líneas en blanco para entrar: partí la subtarea o reportá el exceso." >&2
  exit 1
fi
exit 0
