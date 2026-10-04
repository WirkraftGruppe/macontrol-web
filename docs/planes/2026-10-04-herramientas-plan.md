# Plan: Presupuesto por subtarea, integración segura, plantilla y agentes registrados
- **slug**: `herramientas-plan`
- **fecha**: 2026-10-04
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): herramientas-plan`. No se escribe acá: el hash se anota en `## Registro de verificación`.
- **objetivo**: el presupuesto de cada subtarea se mide sobre sus propios commits, `worktree-integrar.sh` no borra un worktree con el cwd adentro, la integración del principal es una subtarea numerada que el hook ejecuta, `juez-plan` y `verificador-b` se registran como tipos de agente y el total del veredicto sale de la lista de criterios.
- **fuera de alcance**: todo archivo fuera de `.claude/`, `docs/plantilla-plan.md` y `CLAUDE.md` (salvo este plan); código de la aplicación; `verificar_plan.py` (ejecuta el criterio literal y no cambia); `worktree-crear.sh`.
- **áreas**: infraestructura (herramientas de proceso)
- **seguridad**: no — solo scripts de proceso, agentes y documentación; no toca autenticación, API, fotos, QR, geolocalización, certificados, producción ni datos personales.

## Contexto mínimo

- P-contrato-app-4: `presupuesto.sh` (`.claude/hooks/presupuesto.sh:93-116`) mide el diff por rutas desde `commit_base`; dos subtareas que comparten un archivo se contaminan. Nuevo modo `--subtarea T<n>`: suma las líneas agregadas por los commits no-merge de `commit_base..HEAD` cuyo asunto empieza con `T<n>:` (y `T<n>b:`). El modo por rutas se mantiene (decisión 2026-10-01).
- P-limites-ingreso-17: `worktree-integrar.sh:154` borra el worktree sin mirar el cwd. Hoy la raíz sale de `--show-toplevel` (`:60`), así que invocado desde dentro del worktree ni siquiera lo encuentra. La ruta pasa a buscarse en `git worktree list --porcelain` (el registrado que termina en `/worktrees/<slug>-T<n>`), sin cambiar dónde crea `worktree-crear.sh` (sesiones paralelas anidan bajo `worktrees/<slug>/worktrees/`), y antes de tocar nada se compara el cwd canónico: exit 3.
- P-contrato-app-5: la plantilla usa `### Trabajo del principal (integración de la ola N)` (`docs/plantilla-plan.md:81-150`), que nadie ejecuta (decisión 2026-10-03). **Decisión del usuario (esta sesión, reemplaza a 2026-10-03):** cada ola termina con una subtarea numerada `### T<n> — Integración (principal)`; la de la última ola es la última subtarea. `test_verificar_plan.py:855` exige el formato viejo y se reemplaza.
- P-contrato-app-3, diagnóstico comprobado: el frontmatter de `.claude/agents/juez-plan.md` y `verificador-b.md` no es YAML válido; su `description` sin comillas contiene `: ` y `yaml.safe_load` da `mapping values are not allowed here`. Los otros cuatro agentes parsean (CRLF no es la causa: `verificador.md` lo tiene y se registra).
- P-contrato-app-12: el veredicto de `verificador.md:162-163` (`<n> criterios en FALLA de <m>`) se escribía de memoria; pasa a contarse sobre las líneas de criterio del informe. `verificador-b.md` es idéntico salvo name/description/model/título.

## Olas

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1, T2, T3, T4 | ninguna (solo `.claude/`, `docs/plantilla-plan.md`, `CLAUDE.md`) |
| 2 | T5 (integración, principal) | ninguna |

Archivos disjuntos entre T1–T4. Sus presupuestos usan el modo por rutas, con rutas que no se solapan: el modo `--subtarea` todavía no existe en sus ramas. T5 lo usa una vez integrado T1.

## Subtareas

### T1 — Modo por subtarea en `presupuesto.sh`

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `.claude/hooks/presupuesto.sh`, `.claude/hooks/test_presupuesto.py`
- **No puede tocar**: `docs/planes/`, `.claude/hooks/verificar_plan.py`, todo otro archivo
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § hooks y tests de hooks
- **Worktree**: sí
- **Ruta**: delegada (implementador) · Evidencia: informe + verificadores · Commit: `T1: …`
- **Presupuesto**: 300 líneas agregadas
- **Qué hacer**: forma nueva `presupuesto.sh <repo> <base> <max> --subtarea T<n>[a-z]?` (con rutas además, o id inválido → exit 2). Toma `git log --no-merges <base>..HEAD`; cuenta los commits cuyo asunto empieza con `T<n>:` o `T<n>b:` (si el id ya trae letra, solo el exacto; `T1` no cuenta `T10:`); suma por archivo las agregadas de `git diff-tree --no-commit-id --numstat -r <hash>` (binarios listados con 0). Sin ningún commit con el prefijo, el total es 0 (exit 0) y la salida dice `sin commits T<n>: desde <base>`. Lo no commiteado no cuenta y se avisa en la salida; los commits del rango sin prefijo `T…:` se listan por stderr como informativo. Misma salida (`total de líneas agregadas: …`, top 10), mismos códigos 0/1/2 y misma resolución de `'<commit_base>'`. Modo por rutas sin cambios. Cabecera de uso actualizada.
- **Criterios**:
  - `[test]` `py -3 -m pytest .claude/hooks/test_presupuesto.py::test_modo_subtarea_mide_solo_commits_con_prefijo -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_presupuesto.py::test_dos_subtareas_mismo_archivo_no_se_suman -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_presupuesto.py::test_modo_rutas_sigue_funcionando -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_presupuesto.py::test_modo_subtarea_ignora_merges_y_cuenta_sufijo_b -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_presupuesto.py::test_modo_subtarea_rechaza_rutas_e_id_invalido -q`
  - `[cmd]` `py -3 -m pytest .claude/hooks/test_presupuesto.py -q`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 .claude/hooks/presupuesto.sh .claude/hooks/test_presupuesto.py`

### T2 — `worktree-integrar.sh` no borra un worktree con el cwd adentro

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `.claude/hooks/worktree-integrar.sh`, `.claude/hooks/test_worktree.py`
- **No puede tocar**: `docs/planes/`, `.claude/hooks/worktree-crear.sh`, todo otro archivo
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § worktrees y tests de hooks
- **Worktree**: sí
- **Ruta**: delegada (implementador) · Evidencia: informe + verificadores · Commit: `T2: …`
- **Presupuesto**: 200 líneas agregadas
- **Qué hacer**: la ruta del worktree de la subtarea sale de `git worktree list --porcelain`: el registrado cuya ruta normalizada termina en `/worktrees/<slug>-T<n>`, prefiriendo el que está bajo `git rev-parse --show-toplevel` si hay más de uno (funciona invocado desde dentro). Antes del paso 1 y de cualquier modificación: si `pwd -P` normalizado (cygpath -m, minúsculas) es igual o está debajo de `cd "$ruta_sub" && pwd -P` normalizado, mensaje "el directorio actual está dentro de <ruta>; salir del worktree antes de integrar" y exit 3 sin tocar nada. Si `git worktree remove` falla igual, el mensaje sugiere que otro shell tiene el cwd adentro. Exit 3 documentado en la cabecera.
- **Criterios**:
  - `[test]` `py -3 -m pytest .claude/hooks/test_worktree.py::test_integrar_aborta_si_cwd_esta_dentro -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_worktree.py::test_integrar_aborta_si_cwd_esta_en_subcarpeta_del_worktree -q`
  - `[cmd]` `py -3 -m pytest .claude/hooks/test_worktree.py -q`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 200 .claude/hooks/worktree-integrar.sh .claude/hooks/test_worktree.py`

### T3 — Agentes: frontmatter válido, total del veredicto, juez y prefijo de commits

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `.claude/agents/juez-plan.md`, `.claude/agents/verificador.md`, `.claude/agents/verificador-b.md`, `.claude/agents/implementador.md`, `.claude/hooks/test_agentes.py`
- **No puede tocar**: `docs/planes/`, `.claude/agents/auditor-seguridad.md`, `.claude/agents/refutador.md`, `CLAUDE.md`, `docs/plantilla-plan.md`
- **Skill a leer antes**: `writing-for-agents` (skill del usuario) y `.claude/skills/convenciones-proyecto/SKILL.md` § tests de hooks
- **Worktree**: sí
- **Ruta**: delegada (implementador) · Evidencia: informe + verificadores · Commit: `T3: …`
- **Presupuesto**: 200 líneas agregadas
- **Qué hacer**: (1) `description` entre comillas dobles en `juez-plan.md` y `verificador-b.md`, mismo texto; `test_agentes.py` nuevo: todo `.claude/agents/*.md` tiene frontmatter que `yaml.safe_load` acepta, `name` igual al nombre del archivo y `description` no vacía. (2) `verificador.md` y `verificador-b.md`: el veredicto se calcula contando las líneas de criterio del informe (`<m>` = criterios listados, `<n>` = los que dicen FALLA), nunca de memoria; mismo texto en los dos. (3) `juez-plan.md` (b): un `[cmd]` de presupuesto usa `--subtarea T<n>` o rutas que no se solapan con las de otra subtarea; la integración del principal es `### T<n> — Integración (principal)` con fila en la tabla y un encabezado de integración que no sea `### T<n>` es hallazgo. (c): las rutas de presupuesto de dos subtareas no se solapan (por segmento). (4) `implementador.md`: el informe agrega una sección `## Commits` con la frase "cada commit de esta subtarea lleva el prefijo T<n>: (los hace el principal)".
- **Criterios**:
  - `[test]` `py -3 -m pytest .claude/hooks/test_agentes.py::test_frontmatter_de_agentes_es_yaml_valido -q`
  - `[grep-1]` `grep -n '^description: "' .claude/agents/juez-plan.md`
  - `[grep-1]` `grep -n '^description: "' .claude/agents/verificador-b.md`
  - `[grep-1]` `grep -n "contando las líneas de criterio" .claude/agents/verificador.md`
  - `[grep-1]` `grep -n "contando las líneas de criterio" .claude/agents/verificador-b.md`
  - `[grep-1]` `grep -n -- "--subtarea T<n>" .claude/agents/juez-plan.md`
  - `[grep-1]` `grep -n "Integración (principal)" .claude/agents/juez-plan.md`
  - `[grep-1]` `grep -n "no se solapan" .claude/agents/juez-plan.md`
  - `[grep-1]` `grep -n "^## Commits" .claude/agents/implementador.md`
  - `[grep-1]` `grep -n "lleva el prefijo" .claude/agents/implementador.md`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 200 .claude/agents .claude/hooks/test_agentes.py`

### T4 — Plantilla, CLAUDE.md y su test

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `docs/plantilla-plan.md`, `CLAUDE.md`, `.claude/hooks/test_verificar_plan.py`
- **No puede tocar**: `docs/planes/`, `.claude/hooks/verificar_plan.py`, `.claude/agents/`
- **Skill a leer antes**: `writing-for-agents` (skill del usuario) y `.claude/skills/convenciones-proyecto/SKILL.md` § tests de hooks
- **Worktree**: sí
- **Ruta**: delegada (implementador) · Evidencia: informe + verificadores · Commit: `T4: …`
- **Presupuesto**: 250 líneas agregadas
- **Qué hacer**: `docs/plantilla-plan.md`: cada `### Trabajo del principal (integración de la ola N)` pasa a `### T<n> — Integración (principal)` con Ola, Depende de, Pasos, Presupuesto y Criterios (la de la última ola es la última subtarea numerada); filas nuevas en `### Estado de subtareas` y `### Corridas`; presupuestos de ejemplo con `bash .claude/hooks/presupuesto.sh . '<commit_base>' <N> --subtarea T<n>`; regla escrita en el comentario de reglas: las rutas de presupuesto (si se usan) no se solapan entre subtareas; comentario de integración por ola actualizado. `CLAUDE.md` § 4 "Presupuesto de líneas": forma `--subtarea T<n>` (commits `T<n>:`/`T<n>b:`, sin merges) y la regla de rutas que no se solapan; § 5 "Crear e integrar": la integración de cada ola es `### T<n> — Integración (principal)` y el hook ejecuta sus criterios; `worktree-integrar.sh` se corre desde la raíz, no desde dentro del worktree (exit 3). `test_verificar_plan.py`: reemplazar `test_plantilla_integracion_de_ola_fuera_de_las_tareas` por `test_plantilla_integracion_es_subtarea_numerada` (`parsear_plan` ve la integración como `T<n>` con el criterio `T1: integra <slug>-T1`, la última T numerada es una integración, el cierre global sigue en 6).
- **Criterios**:
  - `[test]` `py -3 -m pytest .claude/hooks/test_verificar_plan.py::test_plantilla_integracion_es_subtarea_numerada -q`
  - `[grep-1]` `grep -n "^### T[0-9]* — Integración (principal)" docs/plantilla-plan.md`
  - `[grep-1]` `grep -n -- "--subtarea T<n>" docs/plantilla-plan.md`
  - `[grep-0]` `grep -n "^## Trabajo del principal" docs/plantilla-plan.md`
  - `[grep-0]` `grep -n "Trabajo del principal" docs/plantilla-plan.md`
  - `[grep-1]` `grep -n "no se solapan" docs/plantilla-plan.md`
  - `[grep-1]` `grep -n -- "--subtarea T<n>" CLAUDE.md`
  - `[grep-1]` `grep -n "Integración (principal)" CLAUDE.md`
  - `[cmd]` `py -3 -m pytest .claude/hooks/test_verificar_plan.py -q`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 docs/plantilla-plan.md CLAUDE.md .claude/hooks/test_verificar_plan.py`

### T5 — Integración (principal)

- **Ola**: 2
- **Depende de**: T1, T2, T3, T4
- **Puede tocar**: `docs/planes/2026-10-04-herramientas-plan.md` (solo debajo del corte)
- **No puede tocar**: todo otro archivo
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § worktrees
- **Worktree**: no
- **Ruta**: inline (principal)
- **Presupuesto**: no aplica: T5 no escribe código; sus cambios al plan van en commits `registro: …`. En su lugar, un criterio usa el modo nuevo sobre T1 ya integrada (los merges `T1: integra …` no cuentan).
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/herramientas-plan` de cada subtarea, no los informes.
  2. Desde la raíz: `bash .claude/hooks/worktree-integrar.sh herramientas-plan T<n> plan/herramientas-plan <rutas>` para T1, T2, T3 y T4.
  3. En `## Pendientes que deja este plan`: decisiones nuevas y `cierra:` de P-contrato-app-3, -4, -5, -12 y P-limites-ingreso-17.
- **Criterios**:
  - `[cmd]` `git log --oneline HEAD | grep -q "T1: integra herramientas-plan-T1"`
  - `[cmd]` `git log --oneline HEAD | grep -q "T2: integra herramientas-plan-T2"`
  - `[cmd]` `git log --oneline HEAD | grep -q "T3: integra herramientas-plan-T3"`
  - `[cmd]` `git log --oneline HEAD | grep -q "T4: integra herramientas-plan-T4"`
  - `[cmd]` `py -3 -m pytest .claude/hooks -q`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 --subtarea T1`
  - `[cmd-falla]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 0 --subtarea T1`

## Criterios de cierre global

- `[cmd]` `py -3 -m pytest .claude/hooks -q`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-04-herramientas-plan.md herramientas-plan`

## Registro de verificación

commit_base: <hash del commit docs(plan): herramientas-plan>

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | pendiente |
| T2 | pendiente |
| T3 | pendiente |
| T4 | pendiente |
| T5 | pendiente |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|

## Pendientes que deja este plan

### Problemas

### Decisiones

### Cierra
