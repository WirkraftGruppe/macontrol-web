#!/usr/bin/env bash
# Verifica que un plan no cambió, arriba de "## Registro de verificación", respecto del
# único commit que lo congeló (el commit cuyo ASUNTO es "docs(plan): <slug>").
#
# Uso: congelado.sh <plan.md> <slug>
#   exit 0 → recorte idéntico al congelado (contrato intacto); por stdout va el hash completo
#            del commit congelado, y nada más
#   exit 1 → el recorte difiere (el diff va por stderr), o hay más de un commit de congelado
#            ("CONTRATO MODIFICADO: <n> commits docs(plan): revisar a mano" y la lista por
#            stderr): un contrato recongelado no se ejecuta, lo decide el usuario
#   exit 2 → no hay commit "docs(plan): <slug>", el plan no está en ese commit o uso inválido
#            (CONTRATO NO CONGELADO)
#
# Solo cuenta el ASUNTO del commit (`git log --format='%H%x09%s'`), nunca el cuerpo: un commit
# con "docs(plan): <slug>" en una línea del cuerpo no congela nada. El asunto debe ser igual a
# "docs(plan): <slug>" o empezar exactamente con "docs(plan): <slug> — " (em dash, p. ej.
# "— modificado: <motivo>"). Así un slug que es prefijo de otro ("esquema" / "esquema-agentes")
# no coincide con commits ajenos. La comparación es de bytes (awk con LC_ALL=C), sin regex. El
# slug se valida contra [a-z0-9-] (el formato de los slugs de los planes).
#
# Se compara ignorando "\r": con core.autocrlf=true, git show devuelve LF y el archivo en
# disco puede tener CRLF.
set -u

if [ "$#" -ne 2 ] || [ -z "$1" ] || [ -z "$2" ]; then
  echo "uso: congelado.sh <plan.md> <slug>" >&2
  exit 2
fi

plan="$1"
slug="$2"

# Slug válido: minúsculas, dígitos y guiones, sin empezar por guion. Cualquier otro carácter
# podría ser un metacarácter de regex, así que se rechaza en lugar de escaparlo.
case "$slug" in
  -* | *[!a-z0-9-]*)
    echo "CONTRATO NO CONGELADO: slug inválido '$slug' (solo [a-z0-9-])" >&2
    exit 2
    ;;
esac

if [ ! -f "$plan" ]; then
  echo "CONTRATO NO CONGELADO: no existe el archivo $plan" >&2
  exit 2
fi

# Los comandos git corren desde la carpeta del plan: así funciona desde cualquier cwd
# (dentro o fuera del repo) y "<commit>:./<archivo>" se resuelve relativo a esa carpeta.
dir_plan="$(dirname -- "$plan")"
base_plan="$(basename -- "$plan")"

if ! cd -- "$dir_plan" 2>/dev/null; then
  echo "CONTRATO NO CONGELADO: no se puede entrar a $dir_plan" >&2
  exit 2
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "CONTRATO NO CONGELADO: $plan no está dentro de un repositorio git" >&2
  exit 2
fi

# 1. Commits de congelado: se filtran por asunto, comparando bytes (sin regex ni filtros de git sobre el mensaje).
asunto="docs(plan): ${slug}"
congelados="$(git -c log.showSignature=false log --format='%H%x09%s' 2>/dev/null \
  | LC_ALL=C awk -v asunto="$asunto" -v prefijo="$asunto — " '
      {
        tab = index($0, "\t")
        if (tab == 0) next
        s = substr($0, tab + 1)
        if (s == asunto || substr(s, 1, length(prefijo)) == prefijo) print
      }')"

if [ -z "$congelados" ]; then
  echo "CONTRATO NO CONGELADO: no hay commit 'docs(plan): ${slug}'" >&2
  exit 2
fi

# 2. Más de un commit de congelado → el contrato se reescribió después de congelarse: no se
# elige ninguno, se reporta y se sale con 1 (lo revisa el usuario).
n="$(printf '%s\n' "$congelados" | wc -l | tr -d '[:space:]')"
if [ "${n:-0}" -gt 1 ]; then
  echo "CONTRATO MODIFICADO: ${n} commits docs(plan): revisar a mano" >&2
  printf '%s\n' "$congelados" >&2
  exit 1
fi

commit="${congelados%%$'\t'*}"

# 3. Comparar los recortes (todo lo anterior a "## Registro de verificación").
congelado="$(mktemp)"
actual="$(mktemp)"
trap 'rm -f "$congelado" "$actual"' EXIT

if ! git show "${commit}:./${base_plan}" >"$congelado" 2>/dev/null; then
  echo "CONTRATO NO CONGELADO: $plan no está en el commit ${commit}" >&2
  exit 2
fi

recortar() {
  tr -d '\r' | sed '/^## Registro de verificación/,$d'
}

recortar <"$congelado" >"$congelado.rec"
recortar <"$base_plan" >"$actual.rec"
trap 'rm -f "$congelado" "$actual" "$congelado.rec" "$actual.rec"' EXIT

if cmp -s "$congelado.rec" "$actual.rec"; then
  printf '%s\n' "$commit"
  exit 0
fi

echo "CONTRATO MODIFICADO: el plan difiere de ${commit} arriba de '## Registro de verificación'" >&2
diff "$congelado.rec" "$actual.rec" >&2
exit 1
