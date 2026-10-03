# Plan: impedir la reversión desde el historial del admin en Visita y Sitio

- **slug**: `historial-revert`
- **fecha**: 2026-10-03
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): historial-revert`. El hash se anota en `## Registro de verificación`.
- **objetivo**: desde el historial del admin ya no se puede revertir una visita realizada a pendiente ni un sitio a un `qr_codigo` anterior; una foto con EXIF corrupto ya no produce un error 500.
- **fuera de alcance** (quedan abiertos en la bitácora):
  - N1, tope de píxeles por formato;
  - N4, el error de `Foto.save` mostrado en el formulario del admin;
  - N5, `observaciones` e `incidencia` editables en una visita realizada (decisión de producto);
  - la reversión del historial en Proyecto, Cliente y otros modelos.
- **áreas**: dominio (admin)
- **seguridad**: sí. Toca roles y permisos del admin, la evidencia y geolocalización de visitas, la invalidación de QR y la subida de fotos. Por eso corre también `auditor-seguridad`.

## Contexto mínimo

- Origen: re-auditoría de `visitas-auditoria` (registro de `docs/planes/2026-10-03-visitas-auditoria.md`), hallazgo N2, bloqueante y confirmado.
- Qué pasa hoy:
  - `SimpleHistoryAdmin.history_form_view` (`venv/Lib/site-packages/simple_history/admin.py:213-250`) arma el formulario con la instancia histórica y guarda con un POST. Solo exige el permiso de ver el historial.
  - En `apps/visitas/admin.py`, `VisitaAdmin` aplica `get_readonly_fields` sobre la versión vieja, que está pendiente. Eso permite volver una visita realizada a pendiente y reescribir sus coordenadas.
  - En `apps/sitios/admin.py:11`, `SitioAdmin` reactiva un `qr_codigo` ya regenerado.
  - `SIMPLE_HISTORY_REVERT_DISABLED` no alcanza: solo oculta el botón.
- Decisión: `VisitaAdmin` y `SitioAdmin` sobrescriben `history_form_view` para lanzar `PermissionDenied` ante un POST. El GET sigue funcionando: se puede consultar el historial. Cada app escribe su propio override de 4 líneas, para no tocar archivos de otro dueño.
- N3: en `apps/visitas/imagenes.py`, si `ImageOps.exif_transpose` lanza una excepción (por EXIF corrupto), se sigue sin rotar en lugar de propagar el error.

## Olas

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1, T2, T3 | ninguna. T1 y T2 tocan archivos disjuntos de `apps/visitas`; T3 toca `apps/sitios`. |

## Subtareas

### T1 — Prohibir revertir una visita desde el historial

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/visitas/admin.py`, `apps/visitas/tests/test_admin.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/visitas/models.py`, `apps/visitas/imagenes.py`, `apps/visitas/services.py`, `apps/visitas/migrations/`, `apps/visitas/tests/test_models.py`, `apps/visitas/tests/test_fotos.py`, `apps/visitas/tests/test_services.py`, cualquier otra app
- **Skill a leer antes**: `.agents/skills/django-security/SKILL.md` § Authorization
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 120 líneas agregadas
- **Qué hacer**:
  - `VisitaAdmin.history_form_view` lanza `PermissionDenied` si `request.method == "POST"`; si no, delega en `super()`.
  - El test, que falla antes del cambio:
    1. crea una visita pendiente y la pasa a realizada con `save()`, para que haya una versión histórica pendiente;
    2. como superusuario, hace GET de `admin:visitas_visita_simple_history` de esa versión y obtiene 200;
    3. hace POST a la misma URL con los datos del formulario y una latitud distinta, y obtiene 403;
    4. comprueba que la visita sigue `realizada`, con su `realizada_en` y su latitud original.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_admin.VisitaAdminTests.test_revertir_desde_historial_esta_prohibido --keepdb`
  - `[grep-1]` `grep -n "def history_form_view" apps/visitas/admin.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check apps/visitas`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-03-historial-revert.md historial-revert)" 120 apps/visitas/admin.py apps/visitas/tests/test_admin.py`

### T2 — Un EXIF corrupto no produce un error 500

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/visitas/imagenes.py`, `apps/visitas/tests/test_fotos.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/visitas/models.py`, `apps/visitas/admin.py`, `apps/visitas/services.py`, `apps/visitas/migrations/`, `apps/visitas/tests/test_models.py`, `apps/visitas/tests/test_services.py`, `apps/visitas/tests/test_admin.py`, cualquier otra app
- **Skill a leer antes**: `.agents/skills/django-security/SKILL.md` § File Upload Security
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 120 líneas agregadas
- **Qué hacer**:
  - En `procesar_imagen`, envolver `ImageOps.exif_transpose(original)` en un `try`. Ante cualquier `Exception`, seguir con la imagen sin rotar.
  - Con un comentario, explicar que la rotación es cosmética y el EXIF se descarta igual.
  - El test, que falla antes del cambio, usa `mock.patch("apps.visitas.imagenes.ImageOps.exif_transpose")` con `side_effect` igual a `struct.error` y a `SyntaxError`, en dos `subTest`. En los dos casos, `Foto.objects.create` con un JPEG real de 2000×1000 guarda la foto, con lado mayor 1600 y sin EXIF.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_fotos.FotoTests.test_exif_corrupto_no_impide_guardar --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check apps/visitas`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-03-historial-revert.md historial-revert)" 120 apps/visitas/imagenes.py apps/visitas/tests/test_fotos.py`

### T3 — Prohibir revertir un sitio desde el historial

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/sitios/admin.py`, `apps/sitios/tests/test_admin.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/sitios/models.py`, `apps/sitios/services.py`, `apps/sitios/migrations/`, `apps/sitios/tests/test_services.py`, `apps/sitios/tests/test_models.py`, cualquier otra app
- **Skill a leer antes**: `.agents/skills/django-security/SKILL.md` § Authorization
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 120 líneas agregadas
- **Qué hacer**:
  - `SitioAdmin.history_form_view` lanza `PermissionDenied` ante un POST; si no, delega en `super()`.
  - El test, en `SitioAdminTests` y que falla antes del cambio:
    1. regenera el QR de un sitio con `services.regenerar_qr`;
    2. como superusuario, hace POST a `admin:sitios_sitio_simple_history` de la versión anterior y obtiene 403;
    3. comprueba que `qr_codigo` sigue siendo el nuevo;
    4. hace GET de esa misma vista y obtiene 200.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_admin.SitioAdminTests.test_revertir_sitio_desde_historial_esta_prohibido --keepdb`
  - `[grep-1]` `grep -n "def history_form_view" apps/sitios/admin.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios --keepdb`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check apps/sitios`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-03-historial-revert.md historial-revert)" 120 apps/sitios/admin.py apps/sitios/tests/test_admin.py`

## Trabajo del principal (integración)

Una sola ola:
1. Crear los worktrees con `worktree-crear.sh historial-revert T<n> plan/historial-revert`.
2. Integrar cada subtarea con `worktree-integrar.sh` y sus rutas.
3. Correr la verificación final y la re-auditoría.
4. Hacer el fast-forward de `main` a `plan/historial-revert`. Incluye `plan/visitas` y `plan/visitas-auditoria`.

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[grep-0]` `grep -rn "fields = \"__all__\"" apps/`
- `[cmd]` `git log --oneline plan/historial-revert | grep -q "T1: integra historial-revert-T1"`
- `[cmd]` `git log --oneline plan/historial-revert | grep -q "T2: integra historial-revert-T2"`
- `[cmd]` `git log --oneline plan/historial-revert | grep -q "T3: integra historial-revert-T3"`
- `[cmd-falla]` `git worktree list | grep -q "historial-revert-T"`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-03-historial-revert.md historial-revert`

## Registro de verificación

commit_base: c2dc617

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | hecha |
| T2 | hecha |
| T3 | hecha |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| 2026-10-03 | T1 | cd8d00c | PASA 5/5 (verificador y verificador-b) | integrada en d7166e1 |
| 2026-10-03 | T2 | 9a0256a | PASA 4/4 (verificador y verificador-b) | integrada |
| 2026-10-03 | T3 | 6d4ea23 | PASA 5/5 (verificador y verificador-b) | integrada |
| 2026-10-03 | TODO | 83e00bd | PASA 25/25 (verificador) y 26/26 (verificador-b) | auditor: N2 cerrado; menor nuevo: el except de T2 tolera archivos corruptos y bomba ICNS (bitácora) |
