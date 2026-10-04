#!/usr/bin/env bash
# Presupuesto de líneas agregadas por subtarea, medido contra el commit base de un plan.
#
# Uso: presupuesto.sh <repo> <base> <max> [rutas...]
#      presupuesto.sh <repo> <base> <max> --subtarea T<n>[a-z]?
#   <repo>  directorio del repositorio git a inspeccionar (. | backend | mobile)
#   <base>  commit contra el que se mide el diff (normalmente commit_base del plan). Si es
#           literalmente `<commit_base>` (entre comillas simples, para que bash no lo tome como
#           redirección), se resuelve con `verificar_plan.py --commit-base`: el hash de la línea
#           `commit_base:` del Registro del plan de la rama (o el activo de la bitácora)
#   <max>   máximo de líneas agregadas permitido (entero >= 0)
#   [rutas] opcional: limita el conteo a esas rutas, relativas a <repo>
#   --subtarea T<n>  modo por subtarea (no admite rutas; el id debe ser T<n> o T<n><letra>)
#
# Modo por subtarea: toma `git log --no-merges <base>..HEAD` y cuenta solo los commits cuyo asunto
# empieza con `T<n>:` o `T<n>b:` (si el id ya trae letra, solo el exacto: `T1` no cuenta `T10:`).
# Suma por archivo las agregadas de `git diff-tree --no-commit-id --numstat -r <hash>` (binarios
# con 0). Sin commits con el prefijo, el total es 0 y la salida dice `sin commits T<n>: desde
# <base>`. Lo no commiteado no cuenta (se avisa) y los commits del rango sin prefijo `T…:` se
# listan por stderr como informativo. Misma salida y mismos códigos que el modo por rutas.
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
# exit 2 → uso inválido, <repo> no es un repositorio git, <base> no existe o `<commit_base>` no
#          se pudo resolver
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

# Modo por subtarea: `--subtarea T<n>[a-z]?` y nada más (con rutas o id inválido, uso inválido).
subtarea=""
if [ "${#rutas[@]}" -gt 0 ] && [ "${rutas[0]}" = "--subtarea" ]; then
  if [ "${#rutas[@]}" -ne 2 ]; then
    echo "uso inválido: --subtarea recibe un único id T<n> y no admite rutas" >&2
    exit 2
  fi
  subtarea="${rutas[1]}"
  if ! printf '%s' "$subtarea" | grep -Eq '^T[0-9]+[a-z]?$'; then
    echo "uso inválido: id de subtarea '$subtarea' (se espera T<n> o T<n><letra>)" >&2
    exit 2
  fi
  rutas=()
fi

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

# Marcador `<commit_base>`: lo resuelve verificar_plan.py (mismo parser que el hook de cierre).
# Python: `py -3`, si no `python3`, si no `python`. La raíz es <repo> y no el entorno heredado.
if [ "$base" = "<commit_base>" ]; then
  verificador="$(dirname "$0")/verificar_plan.py"
  raiz="$(cd "$repo" 2>/dev/null && pwd)"
  if command -v py >/dev/null 2>&1 && py -3 -c "" >/dev/null 2>&1; then
    interprete=(py -3)
  elif command -v python3 >/dev/null 2>&1; then
    interprete=(python3)
  elif command -v python >/dev/null 2>&1; then
    interprete=(python)
  else
    echo "no se pudo resolver '<commit_base>': no hay Python (py -3, python3 ni python)" >&2
    exit 2
  fi
  if ! base="$(CLAUDE_PROJECT_DIR="$raiz" "${interprete[@]}" "$verificador" --commit-base </dev/null | tr -d '\r')" || [ -z "$base" ]; then
    echo "no se pudo resolver '<commit_base>' en '$repo' (ver el motivo arriba)" >&2
    exit 2
  fi
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

if [ -n "$subtarea" ]; then
  crudo="$(mktemp)"
  trap 'rm -f "$detalle" "$crudo"' EXIT
  cuenta=0
  # Commits del rango sin merges, del más nuevo al más viejo: "<hash>\t<asunto>".
  while IFS="$tab" read -r hash asunto; do
    [ -n "$hash" ] || continue
    if [[ "$asunto" == "${subtarea}:"* ]] ||
       { [[ "$subtarea" =~ ^T[0-9]+$ ]] && [[ "$asunto" == "${subtarea}b:"* ]]; }; then
      cuenta=$((cuenta + 1))
      git -C "$repo" diff-tree --no-commit-id --numstat -r "$hash" >>"$crudo"
    else
      echo "informativo: commit sin prefijo ${subtarea}: no cuenta: ${hash:0:7} $asunto" >&2
    fi
  done <<EOF
$(git -C "$repo" log --no-merges --format="%H%x09%s" "$base..HEAD" | tr -d '\r')
EOF
  # Suma por archivo: un mismo archivo en varios commits de la subtarea es una sola fila.
  awk -F'\t' '{ if ($1 == "-") bin[$3] = 1; else suma[$3] += $1; vistos[$3] = 1 }
    END { for (a in vistos) if ((a in bin) && !(a in suma)) printf "0\tbinario\t%s\n", a;
                            else printf "%d\t%d\t%s\n", suma[a], suma[a], a }' "$crudo" >"$detalle"
  if [ -n "$(git -C "$repo" status --porcelain)" ]; then
    aviso="aviso: hay cambios sin commitear; no cuentan en el modo por subtarea"
  fi
else
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
if [ -n "$subtarea" ] && [ "$cuenta" -eq 0 ]; then
  echo "sin commits ${subtarea}: desde $base"
fi
[ -z "${aviso:-}" ] || echo "$aviso"

if [ "$total" -gt "$max" ]; then
  echo "No recortar comentarios, docs, tests ni líneas en blanco para entrar: partí la subtarea o reportá el exceso." >&2
  exit 1
fi
exit 0
