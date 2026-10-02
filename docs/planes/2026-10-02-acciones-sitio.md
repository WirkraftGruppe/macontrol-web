# Plan: Acciones del admin de Sitio con permiso por rol y confirmación (H1-a, H3-a)

- **slug**: `acciones-sitio`
- **fecha**: 2026-10-02
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): acciones-sitio`. No se escribe acá: el hash se anota en `## Registro de verificación`.
- **objetivo**: solo un administrador puede:
  - regenerar QR, con confirmación y hasta 20 sitios por vez;
  - suprimir los datos de un sitio junto con todo su historial, mediante una acción "Suprimir datos (Ley 25.326)" con confirmación.

  "Eliminar" sigue conservando el historial.
- **fuera de alcance**:
  - `AdminSite` restringido por rol (plan de autenticación);
  - `notas`/`horario_acceso` en el historial (H1-b);
  - retención de columnas borradas en disco y backups;
  - `bulk_create`/`update()` de encargados;
  - endurecimiento del resto 10 del CUIT;
  - cambios fuera de `apps/sitios`.
- **áreas**: dominio (modelos y servicios) | panel técnico (admin)
- **seguridad**: sí — permisos por rol sobre acciones que invalidan QR y suprimen datos personales. Corre `auditor-seguridad` al cierre.

## Contexto mínimo

- **Origen:** H1-a y H3-a de la re-auditoría de `docs/planes/2026-10-02-auditoria-dominio.md`, anotados en `docs/bitacora.md` § Problemas abiertos.
- **Estado actual:**
  - `apps/sitios/admin.py:14-22` define `actions = ["regenerar_qr"]`, sin `permissions` y sin confirmación.
  - Django muestra una acción sin `allowed_permissions` a cualquiera que acceda al changelist, aunque solo tenga `view_sitio` (`django/contrib/admin/options.py`).
  - `apps/sitios/services.py` tiene `suprimir_sitio(sitio)` y `regenerar_qr(sitio)`.
- **Permisos.** Lo decide el rol, no `is_staff` (convenciones del proyecto). `User.es_administrador` existe en `apps/accounts/models.py:22`.
  - Regenerar QR exige: activo, `es_administrador` y `has_change_permission`.
  - Suprimir datos exige: activo, `es_administrador` y `has_delete_permission`.
- **Lógica.** Va en `services.py`; el admin solo arma la confirmación y muestra mensajes (`.claude/skills/convenciones-proyecto/SKILL.md:100`).
- **Templates.** `APP_DIRS=True` (`config/settings/base.py:50`). La página de confirmación vive en `apps/sitios/templates/admin/sitios/sitio/confirmar_accion.html`.
- **Test existente.** `apps.sitios.tests.test_admin.SitioAdminTests.test_accion_regenerar_qr_cambia_el_codigo` (plan anterior, cerrado) usa un superusuario con rol por defecto `empleado` y no envía confirmación. Con este plan deja de ver la acción, así que se actualiza:
  - superusuario con `rol=User.Rol.ADMINISTRADOR`;
  - POST con `confirmado=si`.

  Conserva el nombre y la intención.

## Subtareas

### T1 — Restringir y confirmar las acciones de Sitio, y agregar "Suprimir datos"

- **Depende de**: —
- **Puede tocar**: `apps/sitios/admin.py`, `apps/sitios/services.py`, `apps/sitios/templates/admin/sitios/sitio/confirmar_accion.html`, `apps/sitios/tests/test_admin.py`, `apps/sitios/tests/test_services.py`
- **No puede tocar**: `docs/`, `config/`, `apps/accounts/`, `apps/clientes/`, `apps/proyectos/`, `apps/servicios/`, `apps/productos/`, `apps/sitios/models.py`, `apps/sitios/migrations/`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § Prohibiciones de código y § Roles; `.agents/skills/django-security/SKILL.md` (la sección sobre permisos y autorización)
- **Worktree**: no
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 400 líneas agregadas
- **Qué hacer**:
  - `services.py`:
    - `TOPE_REGENERAR_QR = 20`;
    - `regenerar_qr(sitio)` ahora:
      - asigna `sitio._change_reason = "Regeneración de QR"`;
      - guarda con `save(update_fields=["qr_codigo", "qr_impreso_el", "actualizado"])`;
    - `regenerar_qr_lote(sitios)`: si la cantidad supera el tope, levanta `ValidationError` sin cambiar nada; si no, regenera cada uno y devuelve la cantidad;
    - `suprimir_sitios(sitios)`: llama a `suprimir_sitio` por cada sitio y captura `ProtectedError` uno por uno. Devuelve `(suprimidos, con_proyectos)`, donde `con_proyectos` es la lista de sitios que no se pudieron suprimir;
    - docstrings en español.
  - `admin.py`:
    - `actions = ["regenerar_qr", "suprimir_datos"]`;
    - `@admin.action(..., permissions=["regenerar_qr"])` y `@admin.action(description="Suprimir datos (Ley 25.326): borra el sitio y todo su historial", permissions=["suprimir_datos"])`;
    - `has_regenerar_qr_permission` y `has_suprimir_datos_permission` según el Contexto mínimo;
    - si el POST no trae `confirmado`, las dos acciones devuelven un `TemplateResponse` con `confirmar_accion.html`. Esa página:
      - lista los sitios;
      - explica la consecuencia;
      - tiene un formulario con `csrf`, `action`, los `_selected_action` y `confirmado=si`.
    - con confirmación, llaman a los servicios y avisan con `message_user`:
      - tope superado → mensaje de error;
      - sitios con proyectos no suprimidos → mensaje de advertencia que nombra cuáles.
    - el admin no captura `ProtectedError` ni importa `uuid`: eso queda en los servicios.
  - Tests nuevos (abajo) y la actualización del test existente descripta en el Contexto mínimo.
  - `test_staff_sin_rol_administrador_no_ve_las_acciones` usa un usuario con `is_staff=True`, `rol=User.Rol.EMPLEADO` y los permisos `sitios.view_sitio`, `sitios.change_sitio` y `sitios.delete_sitio`. Ese usuario hoy **sí** ve `regenerar_qr`, así que el test falla antes del cambio. El test comprueba dos cosas:
    - que ni `regenerar_qr` ni `suprimir_datos` aparecen en `SitioAdmin.get_actions(request)`;
    - que un POST directo al changelist con `action=regenerar_qr` y `confirmado=si` no cambia el `qr_codigo`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_admin.SitioAdminTests.test_staff_sin_rol_administrador_no_ve_las_acciones --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_admin.SitioAdminTests.test_regenerar_qr_pide_confirmacion --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_admin.SitioAdminTests.test_suprimir_datos_pide_confirmacion --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_admin.SitioAdminTests.test_suprimir_datos_borra_sitio_e_historial --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_services.RegenerarQrTests.test_regenerar_qr_guarda_motivo_en_historial --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_services.RegenerarQrTests.test_regenerar_qr_lote_rechaza_mas_del_tope --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_services.SuprimirSitioTests.test_suprimir_sitios_informa_los_que_tienen_proyectos --keepdb`
  - `[grep-1]` `grep -n 'permissions=\["regenerar_qr"\]' apps/sitios/admin.py`
  - `[grep-1]` `grep -n 'permissions=\["suprimir_datos"\]' apps/sitios/admin.py`
  - `[grep-1]` `grep -n "def has_regenerar_qr_permission" apps/sitios/admin.py`
  - `[grep-1]` `grep -n "def has_suprimir_datos_permission" apps/sitios/admin.py`
  - `[grep-1]` `grep -n "TOPE_REGENERAR_QR = 20" apps/sitios/services.py`
  - `[grep-0]` `grep -nE "ProtectedError|uuid" apps/sitios/admin.py`
  - `[existe]` `apps/sitios/templates/admin/sitios/sitio/confirmar_accion.html`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check apps/sitios`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-02-acciones-sitio.md acciones-sitio)" 400 apps/sitios`

## Trabajo del principal (integración)

Nada: una sola subtarea sobre `main`, sin migraciones nuevas.

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[grep-0]` `grep -rn "fields = \"__all__\"" apps/`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-02-acciones-sitio.md acciones-sitio`

## Registro de verificación

commit_base: e6f47e4

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | pendiente |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| | T1 | | | |
| | TODO | | | |
