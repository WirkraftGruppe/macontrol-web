# Plan: Saneamiento — cerrar los pendientes etiquetados `saneamiento`

- **slug**: `saneamiento`
- **fecha**: 2026-10-04
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): saneamiento`. No se escribe acá: el hash se anota en `## Registro de verificación`.
- **objetivo**: los 17 pendientes con etiqueta `saneamiento` quedan resueltos (15 con código, 2 sin código) salvo la parte de despliegue de P-api-movil-21, sin cambiar el contrato de la API.
- **fuera de alcance**: cambios de modelos o campos (no hay migraciones); el contrato `/api/v1/` (formas de respuesta); la parte de despliegue de P-api-movil-21 (≈81 MB a disco, rutas relativas); el panel; los demás pendientes.
- **áreas**: api | dominio (servicios de visitas, validadores, accounts) | infraestructura (settings, logging, herramientas)
- **seguridad**: sí — toca la resolución del QR (`ResolverQRView`), la subida y el guardado de fotos, el filtro de datos personales en logs, settings (`SESSION_COOKIE_SAMESITE`, `DATA_UPLOAD_MAX_NUMBER_FILES`) y la validación del CUIT; corre también `auditor-seguridad`.

## Contexto mínimo

- Triage del 2026-10-04 (`docs/planes/2026-10-04-triage.md`): `py -3 .claude/hooks/pendientes.py --etiqueta saneamiento` devuelve 17 ids. Diseño aprobado por el usuario antes de fusionar `triage`.
- Nombres de test: se usan las clases existentes (decisión del usuario): `ValidarDatosTests`, `RegistrarDesdeAppTests`, `config.tests.test_registro.RegistroTests`, `config.tests.test_settings.SettingsTests`.
- P-pendientes-heredados-23 (`User.save`) vive en `apps/accounts/models.py:32-44` → T2. `config/settings/*.py` es del principal (Tabla de propiedad) → P-api-movil-21 (solo `DATA_UPLOAD_MAX_NUMBER_FILES = 12`) y P-api-movil-3 (SameSite explícito + comentario en `SPECTACULAR_SETTINGS`) van en T4. SameSite se fija explícito en `base.py` para que el test sobre el módulo falle hoy y no pase por el default de Django.
- Cierres sin código: P-limites-ingreso-13 (`ruff format --check` ya no marca `apps/visitas/tests/test_services.py`; queda solo `apps/sitios/models.py:60`, que resuelve T2); P-pendientes-heredados-29 (`apps/web/tests/test_base.py:17` y `:22` ya afirman `<html lang="es" data-tema="oscuro">`, distinto del selector de `:12`).
- P-api-movil-21 no se cierra: también lleva la etiqueta `despliegue`; este plan resuelve solo `DATA_UPLOAD_MAX_NUMBER_FILES`.
- P-limites-ingreso-12: `py -3 -W error -m pytest …test_pendientes.py` pasa hoy por el `.pyc` cacheado; el criterio de T3 usa `compile()` con `-W error`, que hoy falla.
- P-pendientes-heredados-14: quitar el `noqa` y partir la línea rompe el `[grep-1]` congelado de `docs/planes/2026-10-02-auditoria-dominio.md:66`; ese plan está fusionado y el hook no lo vuelve a correr (queda como decisión).
- Regla CUIT (`apps/clientes/validators.py`): resto 10 es válido solo con prefijo 23 o 33 y dígito 9; con otro prefijo, `ValidationError`; los registros ya cargados no se revalidan (el validador solo corre en `full_clean`).

## Olas

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1 (visitas), T2 (sitios, clientes, accounts, `config/registro.py`), T3 (`.claude`) | ninguna (ningún cambio altera modelos ni campos) |
| 2 | T4 (integración y settings, principal) | ninguna |

Archivos disjuntos entre T1, T2 y T3.

## Subtareas

### T1 — visitas: planillas, servicio de la app, fotos

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/visitas/planillas.py`, `apps/visitas/services.py`, `apps/visitas/imagenes.py`, `apps/visitas/models.py`, `apps/visitas/serializers.py` (solo para importar los topes desde un lugar común, sin cambiar respuestas), `apps/visitas/tests/**`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/api/`, otras apps
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` y la skill de Django/DRF de `.agents/skills/` (§ servicios y tests)
- **Worktree**: sí (`worktrees/saneamiento-T1`)
- **Ruta**: delegada (implementador) · Evidencia: informe + verificadores · Commit: `T1: …`
- **Presupuesto**: 400 líneas agregadas
- **Qué hacer**:
  - P-api-movil-13: en `planillas.py` (`:47`, `:52`), comparar las opciones con tipo estricto (`valor not in opciones` hoy acepta `True` contra una opción `1`); `_es_numero` ya excluye `bool`, así que `test_booleano_no_vale_como_numero` tiene que ejercitar un campo con opciones numéricas y fallar antes del cambio de `:47`/`:52`. Además, un tope de dígitos a los números en `_es_numero` (`:10-15`).
  - P-api-movil-17: `registrar_visita_desde_app` (`services.py:138`) aplica `MAX_FOTOS` y `MAX_PRODUCTOS` (hoy en `serializers.py:15-18`; se mueven a un lugar común sin cambiar sus valores; `serializers.py` los sigue exponiendo porque `apps/visitas/api_views.py:23-25` los importa de ahí y no está en `Puede tocar`); `_armar_productos` (`:98-121`) busca todos los productos en una sola consulta.
  - P-api-movil-18: si el INSERT de `Foto` falla después de `imagen.save` (`models.py:144-145`), se borra el archivo; un error en `storage.delete` dentro del `finally` (`services.py:236-240`) no tapa la excepción original; docstring: "no debe llamarse dentro de otro `atomic`".
  - P-api-movil-19: `cliente_uuid` obligatorio (`None` → `ValidationError`, nunca `VisitaDuplicada`) y rango de lat/lng (±90/±180) validado antes de guardar.
  - P-pendientes-heredados-5: en `imagenes.py:69-78`, mensaje propio para `DecompressionBombError`.
  - P-contrato-app-11: en `test_atraso.py:44`, comprobar el count y el id devuelto, y fijar `ATRASO_MAXIMO_HORAS=168` en el primer POST.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_planillas.ValidarDatosTests.test_booleano_no_vale_como_numero --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_planillas.ValidarDatosTests.test_numero_con_demasiados_digitos_se_rechaza --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.RegistrarDesdeAppTests.test_mas_fotos_que_el_tope_se_rechaza --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.RegistrarDesdeAppTests.test_mas_productos_que_el_tope_se_rechaza --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.RegistrarDesdeAppTests.test_productos_se_buscan_en_una_consulta --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.RegistrarDesdeAppTests.test_fallo_del_insert_de_foto_no_deja_archivo_huerfano --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.RegistrarDesdeAppTests.test_error_al_borrar_no_tapa_la_excepcion_original --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.RegistrarDesdeAppTests.test_cliente_uuid_obligatorio --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.RegistrarDesdeAppTests.test_latitud_fuera_de_rango_se_rechaza --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.RegistrarDesdeAppTests.test_longitud_fuera_de_rango_se_rechaza --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_fotos.FotoTests.test_mensaje_de_resolucion_excesiva --keepdb`
  - `[grep-1]` `grep -n "no debe llamarse dentro de otro" apps/visitas/services.py`
  - `[grep-1]` `grep -n "Visita.objects.count(), 1" apps/visitas/tests/test_atraso.py`
  - `[grep-1]` `grep -n "ATRASO_MAXIMO_HORAS=168" apps/visitas/tests/test_atraso.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T1`

### T2 — sitios, clientes, accounts, filtro de logs

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/sitios/api_views.py`, `apps/sitios/models.py`, `apps/sitios/tests/**`, `apps/clientes/validators.py`, `apps/clientes/tests/**`, `apps/accounts/models.py`, `apps/accounts/tests/**`, `config/registro.py`, `config/tests/test_registro.py`
- **No puede tocar**: `docs/planes/`, `config/settings/`, `config/tests/test_settings.py`, `apps/visitas/`, `apps/web/`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` y la skill de Django/DRF de `.agents/skills/` (§ vistas, validadores y tests)
- **Worktree**: sí (`worktrees/saneamiento-T2`)
- **Ruta**: delegada (implementador) · Evidencia: informe + verificadores · Commit: `T2: …`
- **Presupuesto**: 250 líneas agregadas
- **Qué hacer**:
  - P-api-movil-14: en `ResolverQRView` (`api_views.py:35-41`), filtrar también `cliente__activo=True`; responde el mismo 404, con el mismo cuerpo que un QR inexistente.
  - P-api-movil-5: `FiltroDatosPersonales` limpia `exc_text` (o formatea y limpia `exc_info` en `exc_text` y pone `exc_info=None`), para que el traceback no lleve `DETAIL: Key (cuit)=…`.
  - P-pendientes-heredados-13: la regla CUIT del contexto.
  - P-pendientes-heredados-14: quitar el `# noqa: E501` de `sitios/models.py:60` y correr `ruff format` en ese archivo.
  - P-pendientes-heredados-23: `User.save` solo borra `skip_history_when_saving` si lo puso él.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api.ResolverQRTests.test_cliente_inactivo_da_404 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.clientes.tests.test_models.ClienteTests.test_cuit_resto_10_solo_prefijos_afip --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_registro.RegistroTests.test_limpia_exc_info --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_historial.HistorialUserTests.test_save_respeta_skip_history_del_llamador --keepdb`
  - `[grep-0]` `grep -n "noqa: E501" apps/sitios/models.py`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff format --check apps/sitios/models.py`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 --subtarea T2`

### T3 — herramientas: raw string y regla de recuentos del juez

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `.claude/hooks/test_pendientes.py` (solo la línea con `"C:\Windows"`), `.claude/agents/juez-plan.md`, `.claude/hooks/test_agentes.py`
- **No puede tocar**: `docs/planes/`, `.claude/hooks/pendientes.py`, el resto de `.claude/`
- **Skill a leer antes**: `writing-for-agents` (skill del usuario) y `.claude/skills/convenciones-proyecto/SKILL.md` § Comandos canónicos (tests de hooks)
- **Worktree**: sí (`worktrees/saneamiento-T3`)
- **Ruta**: delegada (implementador) · Evidencia: informe + verificadores · Commit: `T3: …`
- **Presupuesto**: 80 líneas agregadas
- **Qué hacer**:
  - P-limites-ingreso-12: `r"C:\Windows"` en `test_pendientes.py`.
  - P-limites-ingreso-16: en `juez-plan.md` § (b), un patrón nuevo, "recuento absoluto que el propio plan altera": todo recuento absoluto sobre datos que el plan cambia es `bloqueante`; tiene que ser relativo ("cierra exactamente N") o ir al cierre global. Excepción: un plan sin código.
  - Un test de contenido en `test_agentes.py` (ya tiene `DIR_AGENTES`).
- **Criterios**:
  - `[cmd]` `py -3 -W error -c "compile(open('.claude/hooks/test_pendientes.py', encoding='utf-8').read(), 'test_pendientes.py', 'exec')"`
  - `[grep-1]` `grep -n "recuento absoluto" .claude/agents/juez-plan.md`
  - `[test]` `py -3 -m pytest .claude/hooks/test_agentes.py::test_juez_plan_cubre_recuentos_absolutos -q`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 80 --subtarea T3`

### T4 — Integración (principal)

- **Ola**: 2
- **Depende de**: T1, T2, T3
- **Puede tocar**: `config/settings/base.py`, `config/tests/test_settings.py`, `docs/planes/2026-10-04-saneamiento.md` (solo debajo del corte)
- **No puede tocar**: todo otro archivo
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § Worktrees y § Variables de entorno
- **Worktree**: no
- **Ruta**: inline (principal) · Commit: `T4: settings de saneamiento`
- **Presupuesto**: 40 líneas agregadas (`--subtarea T4`: los merges no cuentan, el commit de settings sí)
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/saneamiento` por worktree, no los informes.
  2. Desde la raíz (sin `cd` a los worktrees), `bash .claude/hooks/worktree-integrar.sh saneamiento T<n> plan/saneamiento <rutas de Puede tocar>` para T1, T2 y T3.
  3. En `config/settings/base.py`: `DATA_UPLOAD_MAX_NUMBER_FILES = 12` (MAX_FOTOS 10 + margen); `SESSION_COOKIE_SAMESITE = "Lax"` explícito; un comentario en `SPECTACULAR_SETTINGS` que explique que el CSRF incrustado por `?script` depende de ese Lax.
  4. El test `test_samesite_lax_fijado` en `config/tests/test_settings.py`.
  5. Commit `T4: settings de saneamiento`.
- **Criterios**:
  - `[cmd]` `git log --oneline HEAD | grep -q "T1: integra saneamiento-T1"`
  - `[cmd]` `git log --oneline HEAD | grep -q "T2: integra saneamiento-T2"`
  - `[cmd]` `git log --oneline HEAD | grep -q "T3: integra saneamiento-T3"`
  - `[grep-1]` `grep -n "DATA_UPLOAD_MAX_NUMBER_FILES = 12" config/settings/base.py`
  - `[grep-1]` `grep -n 'SESSION_COOKIE_SAMESITE = "Lax"' config/settings/base.py`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_settings.SettingsTests.test_samesite_lax_fijado --keepdb`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff format --check apps config`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 40 --subtarea T4`

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-04-saneamiento.md saneamiento`
- `[cmd]` `py -3 -m pytest .claude/hooks -q`
- `[cmd]` `py -3 -W error -m pytest .claude/hooks/test_pendientes.py -q`
- `[cmd]` `test "$(py -3 .claude/hooks/pendientes.py --etiqueta saneamiento --json | py -3 -c "import json,sys; print(sum(a['id']!='P-api-movil-21' for a in json.load(sys.stdin)['abiertos']))")" -eq 0`

## Registro de verificación

commit_base: cb7b8e3

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | hecha |
| T2 | hecha |
| T3 | hecha |
| T4 | hecha |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| 2026-10-04 | T1–T3 (verificador) | T1 a930aee · T2 84ba784 · T3 ced8515 | PASA — 0 criterios en FALLA de 27 | en sus worktrees |
| 2026-10-04 | T1–T3 (verificador-b) | T1 a930aee · T2 84ba784 · T3 ced8515 | PASA — 0 criterios en FALLA de 27 | en sus worktrees |
| 2026-10-04 | TODO (verificador) | a5d1a74 | PASA — 0 criterios en FALLA de 44 | 275 tests Django; hooks 125 + 1 skip preexistente |
| 2026-10-04 | TODO (verificador-b) | a5d1a74 | PASA — 0 criterios en FALLA de 44 | ídem |
| 2026-10-04 | auditor-seguridad (`cb7b8e3..HEAD`) | a5d1a74 | 0 bloqueantes, 0 importantes, 1 menor (PLAUSIBLE), 5 observaciones | registrados como P-saneamiento-3 a -5 |

## Pendientes que deja este plan

### Problemas

- P-saneamiento-1 [observación] `test_mas_productos_que_el_tope_se_rechaza` y `test_productos_se_buscan_en_una_consulta` (T1) no tienen corrida roja limpia contra el código viejo: la primera roja falló por ítems de prueba inválidos y después de corregirlos no se volvió a correr contra `cb7b8e3` (informe de T1).
- P-saneamiento-2 [menor] El criterio `compile(open(...))` de T3 deja un `ResourceWarning` por el archivo sin cerrar del propio comando; no cambia el exit, es ruido en la salida.
- P-saneamiento-3 [menor] Auditoría (PLAUSIBLE): el enmascarado de `exc_text` (`config/registro.py:27`, `:69-72`) no cubre `DETAIL: Failing row contains (...)` de Postgres, que llevaría la fila entera (coordenadas, `datos`, CUIT) a los logs si falla un NOT NULL o un futuro CheckConstraint. Hoy no hay disparador concreto. Propuesta: segunda sustitución `Failing row contains \(.*?\)\.?$` (MULTILINE) y test con un NOT NULL de `Visita`. El caso `Key (cuit)=…` que motivó el control no puede darse: `Cliente.cuit` no es único.
- P-saneamiento-4 [observación] Auditoría: `validar_datos` solo se llama desde `apps/visitas/services.py:216`; cuando el panel edite `Visita.datos` tiene que pasar por la misma validación, o vuelve el `OverflowError`. Además, `exc_info=None` en el filtro de logs hará perder el traceback si se suma Sentry (LoggingIntegration) o `AdminEmailHandler`, y el filtro no limpia `stack_info` ni una excepción pasada como argumento (`logger.error("x: %s", exc)`).
- P-saneamiento-5 [observación] Auditoría: la `description` de `extend_schema` de `ResolverQRView` (`apps/sitios/api_views.py:28-31`) dice "QR inexistente o de un sitio inactivo" y no menciona el cliente inactivo (deriva de documentación del contrato).

### Decisiones

- 2026-10-04 — Un CUIT con resto 10 es válido solo con prefijo 23 o 33 y dígito 9; con otro prefijo da `ValidationError`; los CUIT ya cargados no se revalidan — AFIP nunca emite resto 10 con otro prefijo (P-pendientes-heredados-13) — reemplaza a: (nada)
- 2026-10-04 — Se quitó el `# noqa: E501` de `apps/sitios/models.py` y la línea quedó con `ruff format`, aunque invalida el `[grep-1]` histórico de `docs/planes/2026-10-02-auditoria-dominio.md:66` — ese plan está fusionado y el hook no lo vuelve a correr — reemplaza a: (nada)
- 2026-10-04 — `SESSION_COOKIE_SAMESITE = "Lax"` y `DATA_UPLOAD_MAX_NUMBER_FILES = 12` se fijan explícitos en `config/settings/base.py` — el CSRF incrustado por `?script` de drf-spectacular depende de Lax; 12 = MAX_FOTOS 10 + margen — reemplaza a: (nada)

### Cierra

- cierra: P-api-movil-13 — opciones con tipo estricto y tope de 15 dígitos en `apps/visitas/planillas.py` (T1)
- cierra: P-api-movil-17 — `MAX_FOTOS`/`MAX_PRODUCTOS` aplicados en `registrar_visita_desde_app` y productos en una sola consulta (T1)
- cierra: P-api-movil-18 — `Foto.save` borra el archivo si falla el INSERT; el error de `storage.delete` no tapa la excepción original; docstring sobre `atomic` (T1)
- cierra: P-api-movil-19 — `cliente_uuid` obligatorio y rango de latitud/longitud validado en el servicio (T1)
- cierra: P-pendientes-heredados-5 — mensaje propio para `DecompressionBombError` en `apps/visitas/imagenes.py` (T1)
- cierra: P-contrato-app-11 — `test_reintento_fuera_del_limite_responde_409` comprueba count e id y fija `ATRASO_MAXIMO_HORAS=168` (T1)
- cierra: P-api-movil-14 — `ResolverQRView` filtra `cliente__activo=True` y responde el mismo 404 que un QR inexistente (T2)
- cierra: P-api-movil-5 — `FiltroDatosPersonales` formatea `exc_info` en `exc_text` y enmascara `Key (campo)=(valor)` (T2)
- cierra: P-pendientes-heredados-13 — regla CUIT resto 10 solo con prefijos 23/33 en `apps/clientes/validators.py` (T2)
- cierra: P-pendientes-heredados-14 — `# noqa: E501` quitado de `apps/sitios/models.py` y línea formateada (T2)
- cierra: P-pendientes-heredados-23 — `User.save` solo borra `skip_history_when_saving` si lo puso él (T2)
- cierra: P-limites-ingreso-12 — `r"C:\Windows"` en `.claude/hooks/test_pendientes.py` (T3)
- cierra: P-limites-ingreso-16 — patrón "recuento absoluto que el propio plan altera" en `juez-plan.md` § (b) (T3)
- cierra: P-api-movil-3 — `SESSION_COOKIE_SAMESITE = "Lax"` explícito, comentado junto a `SPECTACULAR_SETTINGS`, y `test_samesite_lax_fijado` (T4)
- cierra: P-limites-ingreso-13 — sin código: `ruff format --check apps config` pasa (T4); `test_services.py` ya no se marcaba y `sitios/models.py:60` lo resolvió T2
- cierra: P-pendientes-heredados-29 — sin código: `apps/web/tests/test_base.py:17` y `:22` ya afirman `<html lang="es" data-tema="oscuro">`, distinto del selector de `:12`
<!-- P-api-movil-21 no se cierra: este plan resolvió solo `DATA_UPLOAD_MAX_NUMBER_FILES = 12` (T4) y queda abierto por su parte de despliegue. -->
