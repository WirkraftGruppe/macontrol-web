# Plan: Evidencia de pendientes, atraso máximo, token JSON y contrato OpenAPI
- **slug**: `contrato-app`
- **fecha**: 2026-10-04
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): contrato-app`. No se escribe acá: el hash se anota en `## Registro de verificación`.
- **objetivo**: la app móvil recibe un contrato versionado (`docs/api/openapi-v1.yaml`), nunca hereda evidencia que el empleado no declaró, no puede fechar visitas con más de 168 h de atraso y el token deja de aceptar multipart.
- **fuera de alcance**: panel, PDF, límite de cuerpo en el proxy (P-api-movil-20, parte de despliegue), triage del resto de pendientes, carga manual de evidencia (queda para el panel).
- **áreas**: api | dominio (modelos y servicios) | infraestructura
- **seguridad**: sí — endpoint de autenticación (token/refresh), evidencia de visitas que alimenta certificados, fecha de realización. Corre `auditor-seguridad` sobre T1, T2 y T3.

## Contexto mínimo

- P-api-movil-15: `registrar_visita_desde_app` (`apps/visitas/services.py:190`) reutiliza la pendiente propia y le suma fotos/productos que pudo cargar el admin (`apps/visitas/admin.py:121`, inlines editables en pendiente). **Decisión del usuario (esta sesión, reemplaza la letra "409" del 2026-10-04):** si la pendiente tiene fotos o productos, la API crea una visita nueva con `incidencia_asignacion=True`, deja la pendiente intacta y responde **201** normal. `Visita.clean()` rechaza fotos/productos en pendiente; el admin muestra los inlines solo en visitas no pendientes y deja coordenadas/`datos` de solo lectura en pendientes; al completar una pendiente desde la app el servicio vacía `motivo_manual`.
- Consecuencia aceptada: el admin deja de ser canal de carga de evidencia (los inlines en visitas cerradas ya eran de solo lectura). La carga manual queda para el panel. Hoy nada llama a `registrar_visita_realizada` con origen manual, así que no se rompe ningún flujo existente.
- El servicio adjunta fotos con la visita todavía pendiente y recién después la pasa a realizada (`services.py:208-218`). Es válido porque `clean()` solo corre en `full_clean()`, que se ejecuta ya en estado REALIZADA (`services.py:53`).
- P-api-movil-16: `CrearVisitaSerializer.realizada_en` (`apps/visitas/serializers.py:54`) no tiene cota inferior. Nuevo `ATRASO_MAXIMO_HORAS` en `config/settings/base.py` (default 168); un atraso mayor da 400 en `campos.realizada_en` con el límite en el mensaje.
- P-api-movil-20: `ObtenerToken`/`RenovarToken` (`apps/api/views.py:73,95`) usan los parsers por defecto de DRF. Pasan a `parser_classes = [JSONParser]`. El 415 sale antes de parsear el cuerpo.
- Contrato: `SPECTACULAR_SETTINGS` (`config/settings/base.py:148`) es determinista (VERSION fija, sin SERVERS). El YAML se genera con `--file` y se compara con `diff --strip-trailing-cr` (CRLF en Windows).

## Olas

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1, T2 | api (ninguna), visitas (ninguna) |
| 2 | T3 | visitas (ninguna); necesita `ATRASO_MAXIMO_HORAS`, que agrega el principal al integrar la ola 1 |

## Subtareas

### T1 — Aceptar solo JSON en token y renovación

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/api/views.py`, `apps/api/tests/test_auth.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/api/urls.py`, `apps/visitas/`, `.claude/`
- **Skill a leer antes**: `.agents/skills/django-rest-framework/SKILL.md` § parsers / views; `.agents/skills/jwt-security/SKILL.md`
- **Worktree**: sí
- **Ruta**: delegada (implementador)
- **Presupuesto**: 150 líneas agregadas
- **Qué hacer**: `parser_classes = [JSONParser]` en `ObtenerToken` y `RenovarToken`. Tests: un multipart con archivo a `/api/v1/auth/token/` y a `/refresh/` responde 415 con el formato `{"detalle","campos"}`. Además, con `mock.patch` sobre el `MultiPartParser` de Django (`django.http.request`), el test comprueba que no se parsea el cuerpo, es decir que no se escribe ningún temporal.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_auth.AuthApiTests.test_token_rechaza_multipart_con_415 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_auth.AuthApiTests.test_renovar_rechaza_multipart_con_415 --keepdb`
  - `[cmd]` `test "$(grep -c 'parser_classes = \[JSONParser\]' apps/api/views.py)" -eq 2`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 150 apps/api`

### T2 — Una pendiente no lleva evidencia; la app no la hereda

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/visitas/models.py`, `apps/visitas/admin.py`, `apps/visitas/services.py`, `apps/visitas/tests/test_models.py`, `apps/visitas/tests/test_admin.py`, `apps/visitas/tests/test_api.py`, `apps/visitas/tests/test_services.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/api/`, `apps/visitas/serializers.py`, `apps/visitas/migrations/`, `.claude/`
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Models; `.agents/skills/django-expert/SKILL.md` § admin
- **Worktree**: sí
- **Ruta**: delegada (implementador)
- **Presupuesto**: 400 líneas agregadas
- **Qué hacer**:
  - **Modelo.** `Visita.clean()`: si `pk` existe y el estado es PENDIENTE, rechaza la visita con `fotos` o `productos`.
  - **Admin.** `VisitaAdmin.get_inlines()` devuelve `()` cuando la visita es nueva o está pendiente. En pendientes y en el alta, `latitud`, `longitud`, `precision_m` y `datos` quedan de solo lectura.
  - **Servicio.** En `registrar_visita_desde_app`, si la pendiente propia tiene fotos o productos, crea una visita nueva con `incidencia_asignacion=True` y deja la pendiente intacta. Al completar una pendiente sin evidencia, vacía `motivo_manual`. La respuesta sigue siendo 201.
  - **Tests existentes.** Adaptar los que cargaban evidencia por inline en pendientes, sin borrar lo que cubrían.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_models.VisitaTests.test_pendiente_no_admite_fotos_ni_productos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api.CrearVisitaTests.test_pendiente_con_fotos_crea_nueva_con_incidencia --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api.CrearVisitaTests.test_pendiente_con_productos_crea_nueva_con_incidencia --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_admin.VisitaAdminTests.test_pendiente_no_muestra_inlines_de_evidencia --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_admin.VisitaAdminTests.test_coordenadas_y_datos_solo_lectura_en_pendiente --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.RegistrarDesdeAppTests.test_completar_pendiente_limpia_motivo_manual --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 apps/visitas/models.py apps/visitas/admin.py apps/visitas/services.py apps/visitas/tests/test_models.py apps/visitas/tests/test_admin.py apps/visitas/tests/test_api.py apps/visitas/tests/test_services.py`

### Trabajo del principal (integración de la ola 1)

- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/contrato-app` de T1 y T2.
  2. `bash .claude/hooks/worktree-integrar.sh contrato-app T1 plan/contrato-app apps/api` y `… T2 plan/contrato-app apps/visitas`.
  3. Agregar a `config/settings/base.py` `ATRASO_MAXIMO_HORAS`, leído del entorno con el mismo mecanismo del archivo, default 168, con comentario. Commit `ola 1: ATRASO_MAXIMO_HORAS en settings`.
  4. `bash .claude/hooks/worktree-crear.sh contrato-app T3 plan/contrato-app`.
- **Criterios**: en T4.

### T3 — Rechazar realizada_en con más atraso que el admitido

- **Ola**: 2
- **Depende de**: T2 y la integración de la ola 1
- **Puede tocar**: `apps/visitas/serializers.py`, `apps/visitas/tests/test_atraso.py` (nuevo; puede importar ayudantes de `test_api.py` sin modificarlo)
- **No puede tocar**: `docs/planes/`, `config/`, `apps/api/`, `apps/visitas/services.py`, `apps/visitas/models.py`, `apps/visitas/tests/test_api.py`, `.claude/`
- **Skill a leer antes**: `.agents/skills/django-rest-framework/SKILL.md` § serializers / validation
- **Worktree**: sí
- **Ruta**: delegada (implementador)
- **Presupuesto**: 150 líneas agregadas
- **Qué hacer**: `validate_realizada_en` en `CrearVisitaSerializer` rechaza `realizada_en < timezone.now() - timedelta(hours=settings.ATRASO_MAXIMO_HORAS)`. El mensaje nombra el límite en horas y pide avisar al administrador para cargarla como manual. Tests en `apps/visitas/tests/test_atraso.py`, clase `AtrasoMaximoTests` (POST a `/api/v1/visitas/` como en `CrearVisitaTests`): atraso de 169 h → 400 con `campos.realizada_en` que contiene "168"; 167 h → 201; con `override_settings(ATRASO_MAXIMO_HORAS=24)`, 30 h → 400.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_atraso.AtrasoMaximoTests.test_realizada_en_mas_antigua_que_el_limite_da_400 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_atraso.AtrasoMaximoTests.test_realizada_en_dentro_del_limite_se_acepta --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_atraso.AtrasoMaximoTests.test_limite_de_atraso_sigue_el_setting --keepdb`
  - `[grep-1]` `grep -n "ATRASO_MAXIMO_HORAS" apps/visitas/serializers.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 150 apps/visitas/serializers.py apps/visitas/tests/test_atraso.py`

### Trabajo del principal (integración de la ola 2)

- **Pasos**:
  1. Revisar `cambios.sh` de T3 e integrar con `worktree-integrar.sh contrato-app T3 plan/contrato-app apps/visitas`.
  2. Crear `docs/api/` y generar `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file docs/api/openapi-v1.yaml`.
  3. Agregar en `docs/01-modelo-y-arquitectura.md` §6 el bullet **Contrato de la app**: `docs/api/openapi-v1.yaml` es el contrato de `/api/v1/` que consume la app; todo cambio de respuesta, parámetro o versión de drf-spectacular exige regenerarlo con el comando anterior en el mismo commit, y un criterio de cierre lo compara con el generado.
  4. Commit `contrato: esquema OpenAPI v1 versionado`; cierre global y verificación `TODO` (verificador y verificador-b; refutador si discrepan; auditor-seguridad).
- **Criterios**: en T4.

### T4 — Integración (principal)

- **Ola**: 2 (después de integrar T3)
- **Depende de**: T1, T2, T3
- **Puede tocar**: `config/settings/base.py`, `docs/api/openapi-v1.yaml`, `docs/01-modelo-y-arquitectura.md`
- **No puede tocar**: `docs/planes/` (salvo el Registro y los Pendientes, debajo del corte), `apps/`, `.claude/`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § settings
- **Worktree**: no
- **Ruta**: inline (principal); son los pasos de las dos secciones "Trabajo del principal"
- **Presupuesto**: 40 líneas agregadas (sin contar el YAML generado)
- **Criterios**:
  - `[cmd]` `git log --oneline HEAD | grep -q "T1: integra contrato-app-T1"`
  - `[cmd]` `git log --oneline HEAD | grep -q "T2: integra contrato-app-T2"`
  - `[cmd]` `git log --oneline HEAD | grep -q "T3: integra contrato-app-T3"`
  - `[grep-1]` `grep -n "ATRASO_MAXIMO_HORAS" config/settings/base.py`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 40 config/settings/base.py docs/01-modelo-y-arquitectura.md`

## Criterios de cierre global

- `[existe]` `docs/api/openapi-v1.yaml`
- `[cmd]` `T=$(mktemp) && PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file "$(cygpath -w "$T")" && diff -q --strip-trailing-cr "$T" docs/api/openapi-v1.yaml; r=$?; rm -f "$T"; exit $r`
- `[grep-1]` `grep -n "openapi-v1.yaml" docs/01-modelo-y-arquitectura.md`
- `[grep-1]` `grep -n "ATRASO_MAXIMO_HORAS" config/settings/base.py`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-04-contrato-app.md contrato-app`

## Registro de verificación

commit_base: <hash del commit docs(plan): contrato-app>

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | pendiente |
| T2 | pendiente |
| T3 | pendiente |
| T4 | pendiente |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|

## Pendientes que deja este plan

### Problemas

- P-contrato-app-1 [menor] Sin canal para cargar evidencia de una visita manual hasta que exista el panel (el admin ya no muestra inlines en pendientes).
- P-contrato-app-2 [importante] Diferido a despliegue. Resto de P-api-movil-20: bajo ASGI el cuerpo entero se vuelca a disco antes de la vista; falta el límite de cuerpo en el servidor/proxy.
- P-contrato-app-3 [menor] juez-plan y verificador-b no están registrados como tipos de agente; se corren como general-purpose con su archivo de instrucciones. Registrarlos en la configuración de agentes del proyecto.
- P-contrato-app-4 [importante] presupuesto.sh mide por rutas desde commit_base y no por subtarea: dos subtareas que comparten una ruta se contaminan. Corregir el script para medir los commits T<n>: de cada subtarea; mientras tanto, la plantilla exige rutas de presupuesto disjuntas y juez-plan lo verifica.
- P-contrato-app-5 [menor] 'Trabajo del principal' no es ### T<n> y el hook no lo ejecuta; la plantilla debe convertirlo en la última subtarea numerada.

### Decisiones

- 2026-10-04 — Si la pendiente propia tiene fotos o productos, la API crea una visita nueva con `incidencia_asignacion=True`, deja la pendiente intacta y responde 201 — un 409 no puede crear nada y la app lo leería como fracaso — reemplaza a: 2026-10-04 (P-api-movil-15, solo el código de respuesta)
- 2026-10-04 — `docs/api/openapi-v1.yaml` es el contrato versionado de `/api/v1/`; todo cambio de respuesta lo regenera en el mismo commit — la app necesita un contrato estable fuera del servidor — reemplaza a: (nada)

### Cierra

- cierra: P-api-movil-15 — `Visita.clean()`, inlines del admin solo fuera de pendiente, coordenadas y `datos` de solo lectura en pendiente, `motivo_manual` vaciado y visita nueva con incidencia ante una pendiente con evidencia (T2)
- cierra: P-api-movil-16 — `ATRASO_MAXIMO_HORAS` (168) y 400 en `realizada_en` (T3)
- cierra: P-api-movil-20 — parcial: token y renovación aceptan solo JSON (T1); la parte del proxy sigue abierta como P-contrato-app-2
