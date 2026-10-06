# Plan: Cierre de puntos de control (modo campo, verificación de ubicación, restos del panel)

<!-- Aprobado por el usuario el 2026-10-06. juez-plan corrió sobre el borrador (5 bloqueantes de propiedad, resueltos abajo). -->

- **slug**: `cierre-puntos`
- **fecha**: 2026-10-06
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): cierre-puntos`. No se escribe acá: el hash se anota en `## Registro de verificación`.
- **objetivo**: un administrador puede dar de alta sitios y puntos con el GPS del teléfono y escanear como un empleado; cada revisión y cada apertura registran a qué distancia del punto se hicieron; el mapa del panel carga las teselas de OSM; se cierran los restos del panel y el contrato `/api/v1/` queda documentado completo.
- **fuera de alcance**: rechazar revisiones por distancia; informes y certificados; sitio público; SSE; cambios en la plantilla de la app; mostrar la foto del punto o la distancia en las fichas del panel (queda como pendiente).
- **áreas**: dominio (visitas, sitios), api (contrato `/api/v1/` cambia), panel, infraestructura (settings)
- **seguridad**: sí — roles y permisos de la API (administrador en la app, endpoints de alta), geolocalización (coordenadas de puntos, sitios y distancia), subida de fotos (foto del punto), settings (Referrer-Policy). Corre `auditor-seguridad` en T6 (sobre T3 y T4) y en T9 (modo campo completo y verificación de ubicación).

## Contexto mínimo

- Las vistas de campo exigen `EsEmpleado` (`apps/accounts/permisos.py:12`): `apps/sitios/api_views.py:62,192` y `apps/visitas/api_views.py:59,81,119,181`. `PlanoImagenView` y `FotoView` ya aceptan `EsEmpleado | EsAdministrador`. No hay endpoints de alta de sitio ni de punto. El token ya admite administradores.
- `Visita.empleado` tiene `limit_choices_to` rol EMPLEADO (`apps/visitas/models.py:42`); `cerrar_visita` actualiza `encargado_actual` y `proxima_visita` (`apps/visitas/services.py:534-551`).
- `_proponer_ubicacion` (`apps/visitas/services.py:252`) propone con `PRECISION_MAXIMA_PROPUESTA_M = 50` (`:25`). `fijar_ubicacion` (`apps/sitios/services.py:77`) fija desde el panel sin limpiar la propuesta. No hay haversine ni setting de distancia.
- P-puntos-control-20: `registrar_revision` distingue "La visita no existe." (`services.py:403`) de "no está abierta o no es suya" (`:404-410`), con 400. P-21: cerrar dos veces da 400 (`services.py:482`; `CerrarVisitaApiTests.test_doble_cierre_da_400`, `test_api.py:506`).
- OSM: no hay `SECURE_REFERRER_POLICY` (Django usa `same-origin` y OSM bloquea sin Referer); `apps/panel/static/panel/mapa.js:27` no lleva `referrerPolicy` y `puntos_mapa.js`/`sitio_mapa.js` dicen `"strict-origin"`; la atribución existe solo dentro de Leaflet (P-panel-11).
- `SITE_URL` ya se recorta con `rstrip("/")` (`config/settings/base.py:159-160`); `P-panel-28` no existe en ningún plan: el criterio queda como test de regresión.
- P-panel-4 (`apps/accounts/panel_views.py:90`), P-panel-5 (`apps/servicios/panel_views.py:89`), P-panel-6 (`apps/proyectos/panel_views.py:68-73`), P-panel-17 (`apps/sitios/panel_views.py:366`, `sitio_mapa.js:99`), P-contrato-app-9 (`apps/api/views.py:74-100` sin `extend_schema`).

**Decisiones del usuario al planificar** (van a `### Decisiones` al cerrar):
1. La visita de un administrador no cuenta como servicio: no toma pendientes, no marca `incidencia_asignacion` y al cerrarse no toca `encargado_actual` ni `proxima_visita`. Sus revisiones sí cuentan para el estado del punto.
2. El modo campo exige `precision_m ≤ PRECISION_MAXIMA_M` (50) para fijar coordenadas. Alta de sitio: coordenadas obligatorias, si no 400. Alta de punto: coordenadas opcionales (sin ellas nace sin coordenadas); con precisión peor, 400. `puntos/<id>/ubicacion/` con precisión peor, 400. En el escaneo de un administrador con precisión peor no se fija nada y la revisión no se rechaza.
3. Verificación de ubicación: `distancia_m` (entero, nulo) e `incidencia_ubicacion` (booleano) en `Revision` y en `Visita` (apertura). Referencia: el punto; si no tiene coordenadas, el sitio; si tampoco, "sin verificar" (`distancia_m` nulo, sin incidencia). Incidencia si `distancia_m > DISTANCIA_MAXIMA_M` (300, rango 50–5000). Nunca rechaza.
4. P-20: inexistente y ajena dan el mismo 404 (`{"detalle": "La visita no existe."}`) en `revisiones/` y `cerrar/`. P-21: cerrar una visita ya cerrada por su usuario con `cierre=empleado` da 200 con la visita; cerrada por el sistema o un administrador, 409.
5. Referrer-Policy `strict-origin-when-cross-origin` en settings y `referrerPolicy` igual en los tres `L.tileLayer`, con atribución visible fuera de Leaflet.

**Cambios respecto del pedido** (resultado de propiedad y de `juez-plan`):
- **Settings primero (T1, principal, en la rama del plan)**: `config/settings/` es del principal y T3 lee `DISTANCIA_MAXIMA_M` y `PRECISION_MAXIMA_M`. La ola 2 ramifica de T1.
- **Ola 2 = B, C1, C2 y D** (cuatro worktrees). C se parte en API (T4) y panel (T5), con archivos disjuntos; solo T4 crea migración. La atribución de la ficha de sitio va a T5 (plantillas de `sitios`).
- **A pasa a la ola 3 como la única subtarea transversal de `apps/panel` (T7)**: la tabla de propiedad admite una por plan, y el tablero necesita los campos de T3. Junta OSM del mapa general, el helper de guardas, el contador del tablero y `registrar_revision_demo`.
- **Permisos de abrir, revisiones, cerrar y `me/visitas`, y "el administrador fija coordenadas al escanear"** los hace T3 (son de `apps/visitas`); resolver y `me/puntos` los hace T10. Se compone `EsEmpleado | EsAdministrador`; nadie toca `apps/accounts/permisos.py`.
- **`test_administrador_resuelve_qr_y_abre_visita`, el flujo de punta a punta y el `extend_schema` del token** van a T8 (ola 3, transversal de api): necesitan T3 y T4 integradas. El yaml lo regenera el principal en T9.
- `CerrarVisitaTests` y `VisitaAjenaTests` son clases nuevas en `apps/visitas/tests/test_api.py` (nombres del pedido); reemplazan `CerrarVisitaApiTests.test_doble_cierre_da_400` y `test_visita_ajena_da_404`.

**Excepciones de propiedad** (aprobadas por el usuario el 2026-10-06 con el plan; ninguna corre en paralelo con el dueño):
1. T1 (principal) escribe `apps/web/tests/test_cabeceras.py` (solo test).
2. T7 (panel, ola 3) escribe `apps/visitas/management/commands/registrar_revision_demo.py` y `apps/visitas/tests/test_comandos.py`, con T3 ya integrada.
3. T8 (api, ola 3) escribe `apps/sitios/tests/test_api.py`, solo dentro de `ModoCampoTests`, con T4 ya integrada.

## Contrato entre subtareas (fijo)

- **Settings (T1)**: `DISTANCIA_MAXIMA_M` (env, default 300, `ImproperlyConfigured` fuera de 50–5000, `leer_distancia_maxima_m()` al estilo de `leer_atraso_maximo_horas`); `PRECISION_MAXIMA_M = 50`; `SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"`.
- **Modelos (T3, `visitas/0008`)**: `Revision` y `Visita` suman `distancia_m = PositiveIntegerField(null=True, blank=True)` e `incidencia_ubicacion = BooleanField(default=False)`; `distancia_m` fuera del historial. `Visita.empleado.limit_choices_to` acepta empleado o administrador. `PRECISION_MAXIMA_PROPUESTA_M` pasa a leer `settings.PRECISION_MAXIMA_M`.
- **`apps/visitas/ubicacion.py` (T3)**: `distancia_m(lat1, lng1, lat2, lng2) -> int` (haversine, R = 6 371 000 m) y `verificar(punto, latitud, longitud) -> tuple[int | None, bool]`.
- **`abrir_visita(*, empleado, proyecto, qr_codigo, latitud=None, longitud=None, precision_m=None)`**; `POST visitas/abrir/` suma esos tres campos opcionales.
- **Fijado por escaneo (T3)**: dentro de `registrar_revision`, con el punto bloqueado (`select_for_update`) y sin coordenadas, guarda lat/lng, limpia `ubicacion_propuesta`, `_history_user` = administrador, `_change_reason = "Ubicación fijada por escaneo de administrador"`. No llama a servicios nuevos de `sitios`.
- **Modelo y servicios (T4, `sitios/0006`)**: `PuntoControl.foto` (`ImageField`, opcional, nombre aleatorio, validación igual a la de `Foto` de visitas). `crear_sitio_en_campo(*, administrador, cliente, nombre, direccion, localidad, latitud, longitud, precision_m)`, `crear_punto_en_campo(*, administrador, sitio, nombre, sector, latitud=None, longitud=None, precision_m=None, foto=None)`, `fijar_ubicacion_en_campo(*, administrador, punto, latitud, longitud, precision_m)`; los tres registran `history_user` y `_change_reason`, y el último limpia `ubicacion_propuesta`. `fijar_ubicacion` no cambia de firma.
- **Rutas nuevas (T4 y T10)**: `POST sitios/` (`api:sitios:alta-sitio`, T4), `POST sitios/<int:pk>/puntos/` (`api:sitios:alta-punto`, T4), `POST puntos/<int:pk>/ubicacion/` (`api:sitios:ubicacion-punto`, T10, responde 200); solo `EsAdministrador`; throttle scope `crear_visita`; cliente y sitio activos.
- **Partición de T4** (modificación del 2026-10-06, decisión del usuario): T4 excedió su presupuesto (567/500) y se parte. T4 conserva modelo, migración, `crear_sitio_en_campo`, `crear_punto_en_campo` y las dos rutas de alta; T10 hace `fijar_ubicacion_en_campo`, `ubicacion-punto` y el permiso de administrador en resolver QR y `me/puntos`.
- **Corrección de la auditoría de T6 (T11)** (modificación del 2026-10-06, decisión del usuario): `cerrar_visita` calcula `hay_posterior` sin contar visitas de administradores, para que una visita de administrador cerrada después no anule el efecto del servicio de un empleado sobre `encargado_actual` y `proxima_visita` (decisión 1).
- **Helper de guardas (T7)**: `apps/panel/demo.py::exigir_entorno_demo()` lanza `CommandError` sin DEBUG, sin `DJANGO_ENV=development` o sin SQLite; lo usan `cargar_demo` y `registrar_revision_demo`.

## Olas

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1 (principal: settings) | — |
| 2 | T2 (accounts, servicios, proyectos: panel) ∥ T3 (visitas) ∥ T4 (sitios API) ∥ T5 (sitios panel), T10 (sitios API, después de integrar T4), T6 (integración y auditoría) | visitas (0008), sitios (0006) |
| 3 | T7 (panel: OSM, guardas, tablero, demo) ∥ T8 (api: flujo modo campo y token) ∥ T11 (visitas: corrección de `hay_posterior`), T9 (integración, contrato, auditoría, navegador) | — |

T4 y T5 son de `sitios` en paralelo con archivos disjuntos; solo T4 crea migración. T10 toca los archivos de T4 y ramifica de `plan/cierre-puntos` con T4 integrada.

## Subtareas

### T1 — Settings: Referrer-Policy, distancia y precisión máximas (principal)

- **Ola**: 1 · **Depende de**: —
- **Puede tocar**: `config/settings/base.py`, `config/tests/test_settings.py`, `apps/web/tests/test_cabeceras.py`
- **No puede tocar**: `docs/planes/`, `apps/**` salvo el test indicado
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Settings
- **Worktree**: no (settings del principal, commit `T1:` en `plan/cierre-puntos`) · **Ruta**: inline
- **Presupuesto**: 150 líneas agregadas
- **Qué hacer**: los tres settings del contrato; tests de cabecera, `SITE_URL` con barra final y rango de distancia.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_cabeceras.ReferrerTests.test_strict_origin_when_cross_origin --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_settings.SiteUrlTests.test_quita_barra_final --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_settings.DistanciaMaximaTests.test_fuera_de_rango_falla --keepdb`
  - `[grep-1]` `grep -n 'SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"' config/settings/base.py`
  - `[grep-1]` `grep -n "PRECISION_MAXIMA_M = 50" config/settings/base.py`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 150 --subtarea T1`

### T2 — Panel: reactivar usuario y campo, filtros de proyectos

- **Ola**: 2 · **Depende de**: T1
- **Puede tocar**: `apps/accounts/panel_views.py`, `apps/accounts/panel_urls.py`, `apps/accounts/templates/accounts/panel/**`, `apps/accounts/tests/test_panel.py`, `apps/servicios/panel_views.py`, `apps/servicios/panel_urls.py`, `apps/servicios/templates/servicios/panel/**`, `apps/servicios/tests/test_panel.py`, `apps/proyectos/panel_views.py`, `apps/proyectos/templates/proyectos/panel/**`, `apps/proyectos/tests/test_panel.py`
- **No puede tocar**: `docs/planes/`, `config/`, modelos y migraciones
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Views; `.claude/skills/convenciones-proyecto/SKILL.md` § Panel
- **Presupuesto**: 300 líneas agregadas
- **Qué hacer**: `UsuarioReactivarView` (POST, mismo `usuarios_gestionables`, enlace en el listado si está inactivo); `CampoReactivarView` (POST, el campo vuelve al esquema y su clave vuelve a usarse); filtros del listado de proyectos solo con activos, ordenados, con `FILTRO_MAXIMO_OPCIONES = 200` por desplegable.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_panel.UsuarioPanelTests.test_reactivar_usuario_desactivado --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.servicios.tests.test_panel.PlanillaPanelTests.test_reactivar_campo_vuelve_al_esquema --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.proyectos.tests.test_panel.ProyectoPanelTests.test_filtros_solo_activos_con_tope --keepdb`
  - `[grep-1]` `grep -n "FILTRO_MAXIMO_OPCIONES = 200" apps/proyectos/panel_views.py`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 --subtarea T2`

### T3 — Visitas: verificación de ubicación, administrador en campo, P-20 y P-21

- **Ola**: 2 · **Depende de**: T1
- **Puede tocar**: `apps/visitas/models.py`, `apps/visitas/migrations/0008_*.py`, `apps/visitas/ubicacion.py`, `apps/visitas/services.py`, `apps/visitas/serializers.py`, `apps/visitas/api_views.py`, `apps/visitas/admin.py`, `apps/visitas/tests/test_ubicacion.py`, `apps/visitas/tests/test_api.py`, `apps/visitas/tests/test_services.py`, `apps/visitas/tests/test_migraciones.py`, `apps/visitas/tests/test_models.py` (los dos últimos agregados el 2026-10-06 por decisión del usuario: 0008 y la decisión 1 invalidan `DESPUES = 0007` y `test_empleado_debe_tener_rol_empleado`)
- **No puede tocar**: `docs/planes/`, `config/`, `apps/sitios/**`, `apps/accounts/permisos.py`, `apps/visitas/management/**`
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Models y § Services; `.agents/skills/django-rest-framework/SKILL.md` § Permissions
- **Presupuesto**: 550 líneas agregadas
- **Qué hacer**:
  - Campos, migración, `ubicacion.py`; `registrar_revision` y `abrir_visita` llenan `distancia_m`/`incidencia_ubicacion` sin rechazar.
  - Administrador: abre sin pendientes ni `incidencia_asignacion`; cerrar no toca el proyecto; fijado por escaneo según el contrato. Empleado: sigue proponiendo.
  - `me/visitas`, `abrir`, `revisiones`, `cerrar` con `EsEmpleado | EsAdministrador`; adaptar los tests que afirman el 403 del administrador (`test_api.py:228`, `:539`).
  - P-20 y P-21 según la decisión 4; `extend_schema` con 404 y 409 de cerrar, 404 y 400 por atraso de revisiones, campos opcionales de abrir.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_ubicacion.UbicacionTests.test_lejos_del_punto_marca_incidencia_sin_rechazar --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_ubicacion.UbicacionTests.test_sin_coordenadas_queda_sin_verificar --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_ubicacion.UbicacionTests.test_usa_el_sitio_si_el_punto_no_tiene_coordenadas --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_ubicacion.UbicacionTests.test_apertura_guarda_distancia --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_ubicacion.UbicacionTests.test_administrador_fija_coordenadas_del_punto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_ubicacion.UbicacionTests.test_empleado_solo_propone --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.AdministradorEnCampoTests.test_no_toma_pendiente_ni_toca_el_proyecto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api.CerrarVisitaTests.test_cerrar_dos_veces_mismo_empleado_da_200 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api.CerrarVisitaTests.test_cerrada_por_otro_da_409 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api.VisitaAjenaTests.test_ajena_e_inexistente_dan_el_mismo_404 --keepdb`
  - `[grep-0]` `grep -n "La visita no está abierta o no es suya" apps/visitas/services.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas apps.api --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 550 --subtarea T3`

### T4 — Sitios API: modo campo del administrador

- **Ola**: 2 · **Depende de**: T1
- **Puede tocar**: `apps/sitios/models.py`, `apps/sitios/migrations/0006_*.py`, `apps/sitios/services.py`, `apps/sitios/serializers.py`, `apps/sitios/api_views.py`, `apps/sitios/api_urls.py`, `apps/sitios/admin.py`, `apps/sitios/tests/test_api.py`, `apps/sitios/tests/test_services.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/sitios/panel_*.py`, `apps/sitios/templates/**`, `apps/sitios/static/**`, `apps/visitas/**`, `apps/accounts/permisos.py`
- **Skill a leer antes**: `.agents/skills/django-rest-framework/SKILL.md` § Permissions y § Serializers
- **Presupuesto**: 500 líneas agregadas
- **Qué hacer**: modelo, `crear_sitio_en_campo`, `crear_punto_en_campo` y las rutas `alta-sitio` y `alta-punto` del contrato; precisión según la decisión 2. La ruta de ubicación, `fijar_ubicacion_en_campo` y los permisos de resolver QR y `me/puntos` son de T10.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api.ModoCampoTests.test_administrador_crea_sitio_y_punto_con_coordenadas --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api.ModoCampoTests.test_empleado_no_puede_crear_sitio_ni_punto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api.ModoCampoTests.test_precision_insuficiente_da_400 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api.ModoCampoTests.test_punto_sin_coordenadas_se_crea --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api.ModoCampoTests.test_cliente_inactivo_da_400 --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 500 --subtarea T4`

### T5 — Sitios panel: alta de punto sin coordenadas, geocodificar por POST, atribución

- **Ola**: 2 · **Depende de**: T1
- **Puede tocar**: `apps/sitios/panel_forms.py`, `apps/sitios/panel_views.py`, `apps/sitios/panel_urls.py`, `apps/sitios/templates/sitios/panel/**`, `apps/sitios/static/sitios/**`, `apps/sitios/tests/test_panel.py`, `apps/sitios/tests/test_geocodificacion.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/sitios/models.py`, `apps/sitios/migrations/**`, `apps/sitios/api_*.py`, `apps/sitios/services.py`, `apps/sitios/serializers.py`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § Panel
- **Presupuesto**: 250 líneas agregadas
- **Qué hacer**: `PuntoAlta` sin latitud/longitud y con la leyenda "La ubicación se toma del primer escaneo" (la edición y la pestaña Mapa siguen fijándola); `Geocodificar` solo por POST con CSRF (GET → 405) y `sitio_mapa.js` manda el texto en el cuerpo; atribución visible de OSM en `_pestana_mapa.html` y `formulario.html`; `referrerPolicy: "strict-origin-when-cross-origin"` en `puntos_mapa.js` y `sitio_mapa.js`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel.PuntoPanelTests.test_alta_sin_campos_de_coordenadas --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_geocodificacion.GeocodificacionTests.test_solo_post_y_texto_fuera_de_la_url --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel.SitioPanelTests.test_ficha_muestra_atribucion_osm --keepdb`
  - `[grep-0]` `grep -n '"?q="' apps/sitios/static/sitios/sitio_mapa.js`
  - `[grep-1]` `grep -n 'referrerPolicy: "strict-origin-when-cross-origin"' apps/sitios/static/sitios/puntos_mapa.js`
  - `[grep-1]` `grep -n 'referrerPolicy: "strict-origin-when-cross-origin"' apps/sitios/static/sitios/sitio_mapa.js`
  - `[cmd]` `node --check apps/sitios/static/sitios/sitio_mapa.js`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 --subtarea T5`

### T10 — Sitios API: ubicación del punto en campo y lectura del administrador

- **Ola**: 2 · **Depende de**: T4 (integrada; worktree desde `plan/cierre-puntos`)
- **Puede tocar**: `apps/sitios/services.py`, `apps/sitios/serializers.py`, `apps/sitios/api_views.py`, `apps/sitios/api_urls.py`, `apps/sitios/tests/test_api.py`, `apps/sitios/tests/test_services.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/sitios/models.py`, `apps/sitios/migrations/**`, `apps/sitios/panel_*.py`, `apps/sitios/templates/**`, `apps/sitios/static/**`, `apps/visitas/**`, `apps/accounts/permisos.py`
- **Skill a leer antes**: `.agents/skills/django-rest-framework/SKILL.md` § Permissions y § Serializers
- **Presupuesto**: 250 líneas agregadas
- **Qué hacer**: `fijar_ubicacion_en_campo` y `POST puntos/<int:pk>/ubicacion/` según el contrato (responde 200 con el punto; precisión peor, 400; punto, sitio o cliente inactivo, 400; inexistente, 404; solo `EsAdministrador`); resolver QR y `me/puntos` con `EsEmpleado | EsAdministrador`, adaptando `test_administrador_no_resuelve_qr` y el 403 de `me/puntos` en `apps/sitios/tests/test_api.py`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api.ModoCampoTests.test_fijar_ubicacion_registra_quien --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api.ModoCampoTests.test_ubicacion_exige_administrador_precision_y_activos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api.ModoCampoTests.test_administrador_resuelve_qr_y_ve_mis_puntos --keepdb`
  - `[grep-1]` `grep -n "ubicacion-punto" apps/sitios/api_urls.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios apps.api --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 --subtarea T10`

### T6 — Integración ola 2 y auditoría (principal)

- **Ola**: 2 · **Depende de**: T2–T5, T10
- **Pasos**: `verificador` y `verificador-b` por subtarea (refutador si discrepan); `cambios.sh`; integrar T2, T5, T4, T3 con `worktree-integrar.sh` y sus rutas; crear el worktree de T10 desde `plan/cierre-puntos` e integrarlo; `auditor-seguridad` sobre T3, T4 y T10 (permisos de administrador, coordenadas, foto); correcciones en `T3b`/`T4b`/`T10b` dentro de su presupuesto; crear worktrees T7 y T8 desde `plan/cierre-puntos`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/cierre-puntos | grep -q "T2: integra cierre-puntos-T2"`
  - `[cmd]` `git log --oneline plan/cierre-puntos | grep -q "T3: integra cierre-puntos-T3"`
  - `[cmd]` `git log --oneline plan/cierre-puntos | grep -q "T4: integra cierre-puntos-T4"`
  - `[cmd]` `git log --oneline plan/cierre-puntos | grep -q "T5: integra cierre-puntos-T5"`
  - `[cmd]` `git log --oneline plan/cierre-puntos | grep -q "T10: integra cierre-puntos-T10"`

### T7 — Panel: mapa con OSM, guardas de demo, tablero y `registrar_revision_demo`

- **Ola**: 3 · **Depende de**: T6
- **Puede tocar**: `apps/panel/templates/panel/mapa.html`, `apps/panel/static/panel/mapa.js`, `apps/panel/demo.py`, `apps/panel/management/commands/cargar_demo.py`, `apps/panel/tablero.py`, `apps/panel/templates/panel/tablero.html`, `apps/panel/tests/test_mapa.py`, `apps/panel/tests/test_cargar_demo.py`, `apps/panel/tests/test_tablero.py`, `apps/visitas/management/commands/registrar_revision_demo.py`, `apps/visitas/tests/test_comandos.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/panel/urls.py`, `apps/visitas/models.py`, `apps/visitas/services.py`
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Management commands; `.claude/skills/convenciones-proyecto/SKILL.md` § Panel
- **Presupuesto**: 400 líneas agregadas
- **Qué hacer**:
  - Atribución visible "© colaboradores de OpenStreetMap" con enlace en `mapa.html`; `referrerPolicy: "strict-origin-when-cross-origin"` en `mapa.js`.
  - Extraer las guardas de `cargar_demo` a `exigir_entorno_demo()` sin cambiar su comportamiento.
  - Contador "Incidencias de ubicación": visitas sin `incidencia_revisada_en` con `incidencia_ubicacion` propia o en alguna revisión.
  - `registrar_revision_demo <nombre de punto> [--empleado U] [--lejos]`: llama primero a `exigir_entorno_demo()`; abre o reutiliza la visita del empleado (por defecto el primero activo) en el proyecto activo del sitio; registra una revisión con foto PIL y las coordenadas del punto, o a ~1 km con `--lejos`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_mapa.MapaTests.test_muestra_atribucion_osm --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_tablero.TableroTests.test_cuenta_incidencias_de_ubicacion --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_comandos.RevisionDemoTests.test_crea_revision_con_foto_y_guardas --keepdb`
  - `[grep-1]` `grep -n 'referrerPolicy: "strict-origin-when-cross-origin"' apps/panel/static/panel/mapa.js`
  - `[grep-1]` `grep -n "exigir_entorno_demo" apps/panel/management/commands/cargar_demo.py`
  - `[grep-1]` `grep -n "exigir_entorno_demo" apps/visitas/management/commands/registrar_revision_demo.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T7`

### T8 — API: flujo modo campo de punta a punta y contrato del token

- **Ola**: 3 · **Depende de**: T6
- **Puede tocar**: `apps/api/views.py`, `apps/api/tests/test_flujo.py`, `apps/api/tests/test_schema.py`, `apps/sitios/tests/test_api.py` (solo `ModoCampoTests`)
- **No puede tocar**: `docs/planes/`, `config/`, `apps/api/urls.py`, `apps/sitios/*.py`, `apps/visitas/**`
- **Skill a leer antes**: `.agents/skills/django-rest-framework/SKILL.md` § Schema
- **Presupuesto**: 250 líneas agregadas
- **Qué hacer**: test "administrador crea sitio y punto desde el campo → empleado escanea ese punto → marcador con coordenadas fijas y sin propuesta"; `test_administrador_resuelve_qr_y_abre_visita`; `extend_schema` de `ObtenerToken` (200 con el cuerpo de los tokens, 401, 415, 429) y `RenovarToken` (descripción en español, 415); `RUTAS_DE_DOMINIO` suma las tres rutas de modo campo.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api.ModoCampoTests.test_administrador_resuelve_qr_y_abre_visita --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_flujo.ModoCampoFlujoTests.test_administrador_crea_y_empleado_escanea_sin_propuesta --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_schema.SchemaTests.test_token_documenta_cuerpo_y_415 --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 --subtarea T8`

### T11 — Visitas: la visita de un administrador no anula el servicio del empleado

- **Ola**: 3 · **Depende de**: T6
- **Puede tocar**: `apps/visitas/services.py`, `apps/visitas/tests/test_services.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/visitas/models.py`, `apps/visitas/migrations/**`, `apps/visitas/management/**`, `apps/visitas/tests/test_comandos.py`, `apps/sitios/**`, `apps/panel/**`, `apps/api/**`
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Services
- **Presupuesto**: 80 líneas agregadas
- **Qué hacer**: en `cerrar_visita`, excluir de `hay_posterior` las visitas cuyo `empleado` es administrador (hallazgo importante de la auditoría de T6, `apps/visitas/services.py:606-615`). Test que reproduce el defecto: empleado con revisión a las 11:00 y visita sin cerrar; administrador que abre, revisa y cierra a las 14:30 en el mismo proyecto; `cerrar_visitas_abiertas` (o `cerrar_visita` con `cierre=sistema`) cierra la del empleado; `encargado_actual` y `proxima_visita` del proyecto se actualizan por la visita del empleado.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.AdministradorEnCampoTests.test_visita_posterior_de_administrador_no_anula_el_servicio --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 80 --subtarea T11`

### T9 — Integración final, contrato, auditoría y prueba en navegador (principal)

- **Ola**: 3 · **Depende de**: T7, T8, T11
- **Pasos**:
  1. Verificar (`verificador` y `verificador-b`) e integrar T7, T8 y T11.
  2. `manage.py spectacular --validate --file docs/api/openapi-v1.yaml`; commit `T9: contrato openapi`.
  3. `auditor-seguridad` sobre el modo campo (un administrador en la app no hace nada que no pueda en el panel) y la verificación de ubicación.
  4. Prueba en navegador del usuario (P-puntos-control-31): mapa general y ficha sin 403 de teselas, arrastre de marcadores, clic de alta, clic de ubicación, sondeo pausado con la pestaña oculta, `cargar_demo` + `registrar_revision_demo` (normal y `--lejos`) y el contador del tablero. Sin el OK del usuario el plan no se cierra.
  5. Verificación `TODO` con `verificador` y `verificador-b` (refutador si discrepan).
- **Presupuesto**: el yaml es generado: `bash .claude/hooks/presupuesto.sh . '<commit_base>' 1500 --subtarea T9`
- **Criterios**:
  - `[cmd]` `git log --oneline plan/cierre-puntos | grep -q "T7: integra cierre-puntos-T7"`
  - `[cmd]` `git log --oneline plan/cierre-puntos | grep -q "T8: integra cierre-puntos-T8"`
  - `[cmd]` `git log --oneline plan/cierre-puntos | grep -q "T11: integra cierre-puntos-T11"`
  - `[cmd]` `T=$(mktemp) && PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file "$(cygpath -w "$T")" && diff -q --strip-trailing-cr "$T" docs/api/openapi-v1.yaml; r=$?; rm -f "$T"; exit $r`
  - `[grep-1]` `grep -n "/api/v1/puntos/{id}/ubicacion/" docs/api/openapi-v1.yaml`
  - `[grep-1]` `grep -n "'415'" docs/api/openapi-v1.yaml`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 1500 --subtarea T9`

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-06-cierre-puntos.md cierre-puntos`

## Registro de verificación

commit_base: 9a284ed

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | hecha |
| T2 | hecha |
| T3 | hecha |
| T4 | hecha |
| T5 | hecha |
| T6 | pendiente |
| T7 | pendiente |
| T8 | pendiente |
| T9 | pendiente |
| T10 | hecha |
| T11 | pendiente |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| 2026-10-06 | T1 | 71eda88 | PASA (verificador 6/6, verificador-b 6/6) | spot check presupuesto: 95/150 |
| 2026-10-06 | T2, T5 | 8a774ff, 8a21588 | PASA (verificador 13/13, verificador-b 13/13) | spot check T2 test_filtros; integradas 6272a20 y 4036b5b |
| 2026-10-06 | T4 | 3c7d1b7 | FALLA formal: 0/8 criterios en FALLA en ambos; contrato MODIFICADO (27b13f8) | aceptado por el usuario; spot check presupuesto 433/500; integrada 2eb5000 |
| 2026-10-06 | T3 | fa9176b | FALLA formal: 0/14 criterios en FALLA en ambos; contrato MODIFICADO (27b13f8) | aceptado por el usuario; spot check presupuesto 534/550; integrada 69b433b |
| 2026-10-06 | T10 (+ 5 [test] de T4) | 660ab2c | FALLA formal: 0/11 criterios en FALLA en ambos; contrato MODIFICADO (27b13f8) | aceptado por el usuario; spot check presupuesto 133/250; integrada aa74093 |

## Pendientes que deja este plan

### Problemas

- P-cierre-puntos-1 [menor] Los botones "Reactivar" de usuarios y campos (T2) usan `class="enlace"`, que no existe en ningún CSS: se ven como botón por defecto.
- P-cierre-puntos-2 [menor] `.env.example` no documenta `DISTANCIA_MAXIMA_M` (T1 no podía tocarlo).
- P-cierre-puntos-3 [menor] `apps/sitios` importa `procesar_imagen` y `validar_tamano_foto` de `apps/visitas` (models y serializers de T4); sin ciclo hoy, conviene un módulo compartido.
- P-cierre-puntos-4 [observación] `precision_m` se valida y no se guarda en altas de sitio/punto ni en `abrir_visita`.
- P-cierre-puntos-5 [menor] `AltaPuntoView` (`apps/sitios/api_views.py:292-314`) no corta por `CONTENT_LENGTH` ni captura `RequestDataTooBig`/`TooManyFieldsSent`/`TooManyFilesSent`: foto enorme se escribe y abre antes del 400, y esos rechazos dan 500; aplicar el patrón de `CrearRevisionView` (auditoría T6).
- P-cierre-puntos-6 [menor] `PuntoControl.foto` es editable en `/admin/` (`apps/sitios/admin.py:85-89`): reemplazar o limpiar deja el archivo huérfano y una imagen sobre el tope de `procesar_imagen` da 500; ponerla en `readonly_fields` (auditoría T6).
- P-cierre-puntos-7 [menor] Desde `/admin/` se puede asignar una visita pendiente a un administrador (`limit_choices_to` acepta administrador): nunca la consume y marca `incidencia_asignacion` a los empleados del proyecto; limitar el campo en `VisitaAdmin` o rechazarlo en `Visita.clean()` (auditoría T6).
- P-cierre-puntos-8 [observación] `fijar_ubicacion_en_campo` y `fijar_ubicacion` guardan la instancia sin `select_for_update`: el historial puede registrar valores viejos de otros campos (auditoría T6).
- P-cierre-puntos-9 [observación] `registrar_revision` bloquea la visita antes de comprobar el dueño: la demora distingue "existe y está activa" de "no existe"; filtrar por `empleado` dentro del `select_for_update` (auditoría T6).
- P-cierre-puntos-10 [observación] El rol que decide si la visita cuenta como servicio se evalúa al cerrar, no al abrir (auditoría T6).
- P-cierre-puntos-11 [observación] Altas de sitio y punto, ubicación, abrir, revisiones y cerrar comparten el cupo `crear_visita` (120/h): un alta de sitio grande en campo lo agota (auditoría T6).

### Decisiones

- 2026-10-06 — T3 puede tocar `test_migraciones.py` y `test_models.py` de visitas — 0008 y la decisión 1 invalidaban dos tests existentes — reemplaza a: (nada)
- 2026-10-06 — T4 se parte en T4 (altas y foto) y T10 (ubicación en campo y lectura del administrador) — T4 excedió su presupuesto (567/500) y no se sube — reemplaza a: (nada)
- 2026-10-06 — El hallazgo importante de la auditoría de T6 (`hay_posterior` cuenta visitas de administradores) se corrige en una subtarea nueva T11 de la ola 3, y los menores quedan como pendientes — contradice la decisión 1 y no entra en el presupuesto de T3 — reemplaza a: (nada)
- 2026-10-06 — Se acepta el FALLA formal de `congelado.sh` por la modificación 27b13f8 en las verificaciones de este plan — la modificación la decidió el usuario; ningún criterio de código falla — reemplaza a: (nada)

### Cierra

<!-- Al cerrar: P-puntos-control-20, -21, -31; P-panel-4, -5, -6, -11, -17; P-contrato-app-9. -->
