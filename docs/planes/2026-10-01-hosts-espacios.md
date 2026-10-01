# Plan: normalizar los espacios de ALLOWED_HOSTS

- **slug**: `hosts-espacios`
- **fecha**: 2026-10-01
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): hosts-espacios`. No se escribe acá: el
  hash se anota en `## Registro de verificación`.
- **objetivo**: `ALLOWED_HOSTS=" a , b "` se lee como `["a", "b"]` en desarrollo y en producción. Sin la corrección, la barrera de desarrollo aborta por un espacio, y en producción el host nunca coincide y responde 400.
- **fuera de alcance**: la barrera según el hosting y la confirmación explícita para las IP privadas. Las dos dependen de que el modo desarrollo corra en un servidor público, y el usuario dejó ese caso para el plan de despliegue (bitácora, problemas abiertos).
- **áreas**: infraestructura
- **seguridad**: sí. Toca `config/settings/prod.py`, aunque el cambio no amplía nada: limpia valores y descarta los vacíos.

## Contexto mínimo

Es un hallazgo menor del auditor en la verificación del plan `hallazgos-esqueleto`. `env.list("ALLOWED_HOSTS")` de django-environ separa por comas, pero no recorta espacios:
- `config/settings/dev.py:16`: `"localhost, 192.168.1.10"` da `" 192.168.1.10"`, que la barrera rechaza como host público.
- `config/settings/prod.py:10`: el host con espacio no coincide nunca con el `Host` de la petición.

Corrección: `[h.strip() for h in env.list(...) if h.strip()]` en los dos módulos.

## Subtareas

### T1 — Recortar espacios y descartar vacíos en ALLOWED_HOSTS

- **Depende de**: —
- **Puede tocar**: `config/settings/dev.py`, `config/settings/prod.py`, `config/tests/test_settings.py`
- **No puede tocar**: `docs/`, `.claude/`, `.agents/`, `config/settings/base.py`, `apps/`, `templates/`, `static/`
- **Skill a leer antes**: `.agents/skills/django-security/SKILL.md` (ALLOWED_HOSTS)
- **Worktree**: no
- **Ruta**: inline (principal) · Evidencia: … · Commit: …
- **Presupuesto**: 60 líneas agregadas
- **Qué hacer**:
  - En `dev.py` y `prod.py`, `ALLOWED_HOSTS` se arma con la lista recortada y sin elementos vacíos. Se mantienen los valores por defecto actuales.
  - Agregar dos tests a `SettingsTests`:
    - `test_dev_recorta_espacios_de_allowed_hosts`: `check` en desarrollo con `"localhost, 192.168.1.10 "` sale con 0.
    - `test_prod_recorta_espacios_de_allowed_hosts`: `shell -c` en producción con `" macontrol.com.ar , ,www.macontrol.com.ar"` imprime `['macontrol.com.ar', 'www.macontrol.com.ar']`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_settings.SettingsTests.test_dev_recorta_espacios_de_allowed_hosts --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_settings.SettingsTests.test_prod_recorta_espacios_de_allowed_hosts --keepdb`
  - `[cmd]` `env -u SECRET_KEY -u DATABASE_URL ALLOWED_HOSTS="localhost, 192.168.1.10 " PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_settings --keepdb`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-01-hosts-espacios.md hosts-espacios)" 60 config/settings/dev.py config/settings/prod.py config/tests/test_settings.py`

## Trabajo del principal (integración)

Nada.

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-01-hosts-espacios.md hosts-espacios`

## Registro de verificación

commit_base: (pendiente)

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | pendiente |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| | T1 | | | |
| | TODO | | | |
