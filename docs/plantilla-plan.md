# Plan: <título corto>

<!--
Copiar a docs/planes/AAAA-MM-DD-<slug>.md.
Flujo (CLAUDE.md § Flujo de trabajo):
  1. Se escribe en modo plan.
  2. Se commitea solo, ANTES de lanzar el primer subagente:  git commit -m "docs(plan): <slug>"
  3. Se anota el hash de ese commit en el Registro (línea `commit_base:`, debajo del corte), nunca
     en el encabezado. Desde ese momento los criterios están congelados.
  4. Cada subtarea se delega con su bloque Criterios copiado literal.
  5. Cada subtarea se commitea (`T<n>: …`) antes de verificarla; las actualizaciones del Registro
     van en commits `registro: …`.
  6. Después de cada subtarea:   verificador  →  <ruta del plan>  T<n>
     Recién con sus criterios en PASA se marca `hecha` en la tabla de estado.
  7. Al final:                    verificador  →  <ruta del plan>  TODO
Todo lo que está entre <> se reemplaza; los comentarios <!-- --> se borran.

Corte del congelado: todo lo anterior a `## Registro de verificación` queda congelado desde el
commit `docs(plan): <slug>` y lo verifica `bash .claude/hooks/congelado.sh <plan> <slug>`
(exit 1 → CONTRATO MODIFICADO; exit 2 → CONTRATO NO CONGELADO). Desde ese encabezado hacia abajo
(commit_base, estado de subtareas, corridas) el principal lo actualiza durante la ejecución.
Un cambio de contrato es un commit nuevo `docs(plan): <slug> — modificado: <motivo>`, decidido por
el usuario.

El hook de cierre (`.claude/hooks/verificar_plan.py`, evento Stop) ejecuta los criterios de las
subtareas en estado `hecha` del plan activo de `docs/bitacora.md`, y los de cierre global cuando
todas están `hecha`. Por eso el estado vive en la tabla del Registro, no en los encabezados.
-->

- **slug**: `<slug>`
- **fecha**: AAAA-MM-DD
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): <slug>`. No se escribe acá: el
  hash se anota en `## Registro de verificación`.
- **objetivo**: <una oración: qué cambia para el usuario final cuando esto está hecho>
- **fuera de alcance**: <qué NO se toca, explícito>
- **áreas**: web | panel | api | dominio (modelos y servicios) | infraestructura
- **seguridad**: sí/no — <si sí: qué toca (auth, roles, get_queryset de la API, fotos, QR, geolocalización, certificados, settings de producción, datos personales) y por lo tanto corre también `auditor-seguridad`>

## Contexto mínimo

<3 a 8 líneas. Qué existe hoy, qué está roto o falta, y la decisión de diseño tomada.
Enlaces a archivos concretos con ruta, y a la sección de `docs/01-modelo-y-arquitectura.md`
que aplica. Sin narrativa.>

## Subtareas

<!--
Reglas para escribir criterios (las hace cumplir el verificador, no el implementador):
- Solo tipos permitidos: [cmd] [cmd-falla] [existe] [no-existe] [grep-1] [grep-0] [test]
- Comandos completos y literales. Los de Django llevan siempre el prefijo canónico:
  PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py …
- Toda subtarea que agrega comportamiento lleva al menos un [test].
- Toda subtarea que corrige un defecto lleva un [test] que reproduzca el defecto.
- Un [test] tiene que ser NUEVO respecto de commit_base.
- Prohibido: "funciona", "tests pasando", "revisado", "sin regresiones", "quedó implementado".
- Dos subtareas no escriben el mismo archivo ni crean migraciones en la misma app en paralelo.
-->

<!-- Las subtareas se llaman siempre T<n>: el hook de cierre solo reconoce `### T<n>` y las filas `| T<n> |`. -->
### T1 — <título imperativo, p. ej. "Crear el modelo Sitio con qr_codigo único">

- **Depende de**: — | T<n>
- **Puede tocar**: `apps/sitios/models.py`, `apps/sitios/migrations/0001_initial.py`, `apps/sitios/tests/test_models.py`
- **No puede tocar**: `docs/planes/`, `config/settings/`, migraciones existentes de otras apps
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Models
- **Worktree**: sí/no
- **Ruta**: inline | delegada · Evidencia: … · Commit: …
- **Presupuesto**: <N> líneas agregadas (por defecto 400)
- **Qué hacer**: <2 a 5 líneas concretas. Qué modelo, qué campo, qué comportamiento.>
- **Criterios**:
  - `[test]` `apps.sitios.tests.test_models.SitioTests.test_qr_codigo_se_genera_al_crear`
  - `[test]` `apps.sitios.tests.test_models.SitioTests.test_qr_codigo_es_unico`
  - `[grep-1]` `grep -n "qr_codigo = models.UUIDField" apps/sitios/models.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . <commit_base> <N> apps/sitios`

### T2 — <título>

- **Depende de**: T1
- **Puede tocar**: …
- **No puede tocar**: `docs/planes/`, …
- **Skill a leer antes**: …
- **Qué hacer**: <…>
- **Criterios**:
  - `[test]` …

## Trabajo del principal (integración)

<Qué hace el principal después de que las subtareas pasan: cablear urls, migrar, ajustar imports,
resolver conflictos. Lleva sus propios criterios igual que una subtarea. Si no hay nada, se
escribe "nada" y la verificación final corre directo.>

- **Criterios**:
  - `[cmd]` `<…>`

## Criterios de cierre global

<!-- Copiar de CLAUDE.md § "Criterios de cierre global". Reemplazar <archivo> y <slug>. -->

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/<archivo>.md <slug>`

## Registro de verificación

<!-- Corte del congelado: desde este encabezado hacia abajo, el principal lo actualiza durante la
ejecución. Lo de arriba no se toca sin un commit `docs(plan): <slug> — modificado: <motivo>`. -->

commit_base: <hash del commit docs(plan): <slug>>

### Estado de subtareas

<!-- Valores: pendiente | en curso | hecha. Una tarea pasa a `hecha` solo después de ver pasar sus criterios. -->

| Tarea | Estado |
|---|---|
| T1 | pendiente |
| T2 | pendiente |

### Corridas

<!-- Lo completa el principal pegando el veredicto del verificador, sin editar. Una línea por
corrida. Un veredicto vale solo para el HEAD verificado. -->

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| | T1 | | | |
| | TODO | | | |
