# Plan: Puntos de control con QR propio, planos y visita como jornada


- **slug**: `puntos-control`
- **fecha**: 2026-10-05
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): puntos-control`. No se escribe acá: el hash se anota en `## Registro de verificación`.
- **objetivo**: cada sitio tiene uno o más puntos de control con su QR, y puede tener planos con un marcador por punto. Una visita pasa a ser la jornada de un empleado (se abre, acumula una revisión por escaneo y se cierra). El panel ve el estado de cada punto, actualizado por sondeo cada 5 s.
- **fuera de alcance**: SSE o WebSockets; informes, certificados y la hoja de etiquetas; sitio público (`/q/<uuid>/` no cambia); app móvil; notificaciones; dibujo de planos; borrado físico de puntos o planos (se desactivan).
- **áreas**: dominio (modelos, migraciones de datos, servicios), api (contrato `/api/v1/` cambia), panel, infraestructura (dependencia `pypdfium2`, un setting)
- **seguridad**: sí — QR (unidad nueva, regeneración por punto), subida y servido de planos (PDF y formatos de imagen no confiables), fotos (cambian de dueño), geolocalización (coordenadas de revisiones y ubicación propuesta de puntos), permisos de la API (imagen del plano, `me/puntos/`, visitas abiertas). Corre `auditor-seguridad` en T7, T10, T14 y T17.

## Contexto mínimo

- Hoy el QR es `Sitio.qr_codigo` (`apps/sitios/models.py:54`). Lo usan `qr.py`, `services.regenerar_qr` (`apps/sitios/services.py:46`, tope 20), `ResolverQRView` (`apps/sitios/api_views.py:18`) y la comparación de `_validar_proyecto_y_qr` (`apps/visitas/services.py:98`). `/q/<uuid>/` (`apps/web/views.py:10`) no busca el código.
- `Visita` (`apps/visitas/models.py:20`) guarda la evidencia de un único escaneo: coordenadas, `cliente_uuid`, `recibida_en`, `realizada_en`, fotos y productos. `registrar_visita_realizada` (`services.py:33`) actualiza el proyecto, y `registrar_visita_desde_app` (`:207`) la usa detrás de `POST visitas/`.
- `CampoPlanilla` (`apps/servicios/models.py:44`) no tiene ámbito, y `esquema_planilla()` (`:21`) devuelve todos los campos activos.
- El mapa del panel (`apps/panel/mapa.py:39`) colorea por `Proyecto.estado_visita` (`apps/proyectos/models.py:113`, `UMBRAL_PROXIMA_DIAS = 7`).
- No existe ningún rasterizador de PDF (`requirements.txt`), ningún test de migraciones ni el comando `cargar_demo`.
- La especificación es `docs/propuestas/2026-10-05-puntos-de-control.md`, aprobada. Reemplaza `docs/01-modelo-y-arquitectura.md` §3.2, §3.4, §3.6–3.8 y §4.

**Decisiones registradas que este plan reemplaza** (van a `### Decisiones` al cerrar):
- 2026-09-29: un QR por sitio.
- 2026-10-02: el tope de 20 para regenerar pasa a contar puntos.
- 2026-10-03: `registrar_visita_realizada` valida coordenadas y foto; ahora valida `registrar_revision`.
- 2026-10-04: el chequeo de atraso estaba en `CrearVisitaSerializer`; pasa al serializer de revisiones.
- 2026-10-03: `Visita.esquema_planilla` guardaba la copia de la planilla. Ahora `Revision.esquema_planilla` copia el ámbito `punto` y `Visita.esquema_planilla` solo el ámbito `visita`.

**Decisiones de diseño de este plan** (las aprueba el usuario con el plan):
1. `pypdfium2` convierte el PDF del plano: la primera página, con el lado mayor de 4000 px como máximo, guardada como PNG. Se aceptan JPG, PNG y PDF; cualquier otro formato da `ValidationError`.
2. `ubicacion_propuesta` se llena solo si el punto no tiene lat/lng, la revisión trae `precision_m ≤ 50` y no hay otra propuesta pendiente.
3. **`POST revisiones/` recibe `qr_codigo`, no el id del punto.** El QR sigue siendo la prueba de presencia (decisión 2026-09-29); el servidor resuelve el punto y exige que pertenezca al sitio del proyecto de la visita.
4. `cerrar_visita` exige al menos una revisión. El cierre por sistema:
   - con revisiones, fija `cerrada_en` en el `realizada_en` de la última revisión, no en la hora del comando;
   - sin revisiones, devuelve la visita a `pendiente` si venía asignada (`asignada_por` no nulo) y si no la deja `cancelada`; en ningún caso toca el proyecto.
5. Estado de un punto (`estado_revision`): `sin_revisar` si no tiene revisiones para ese proyecto; si las tiene, cuenta desde `realizada_en` de la última revisión más `frecuencia_dias`, con `UMBRAL_PROXIMA_DIAS` (sin frecuencia es `al_dia`). Cuentan las revisiones de visitas abiertas y realizadas, no las de canceladas. El punto toma el peor estado entre los proyectos activos del sitio, y el sitio en el mapa, el peor de sus puntos. Gravedad: `vencida` > `sin_revisar` > `proxima` > `al_dia`.
6. Carga manual por puntos: crea una revisión por punto elegido, todas con la planilla de ámbito `punto` del formulario. Fotos y productos quedan en la revisión del primer punto (por `orden`). La visita se cierra con `cierre=administrador` y `cerrada_en` igual a la fecha cargada.
7. `abrir_visita` es idempotente: si el empleado ya tiene una visita abierta para ese proyecto, la devuelve con 200. Si tiene una pendiente asignada, la abre. Si no, crea una con `incidencia_asignacion` cuando otro empleado tiene la pendiente (la regla de hoy).
8. `abrir`, `revisiones` y `cerrar` comparten el scope de throttle `crear_visita` (120/h), sin cambios en settings.
9. `Revision` lleva historial sin `latitud`, `longitud`, `precision_m` ni `datos`, igual que `Visita`, y su evidencia es de solo lectura en el admin.
10. El sondeo HTMX se pausa con la pestaña oculta mediante `apps/sitios/static/sitios/sondeo.js`, que cancela `htmx:beforeRequest` si `document.hidden`. Los filtros de `hx-trigger` (`[cond]`) necesitan `eval` y la CSP lo impide.

**Cambios respecto del pedido:**
- **Transición del QR en la ola 1.** Desde T3 hasta T6, un `Sitio` nuevo recibe automáticamente su punto "General" con el mismo valor de `Sitio.qr_codigo`, y regenerar el QR del punto General también actualiza `Sitio.qr_codigo`. Así los tests y el código que todavía leen `sitio.qr_codigo` no se rompen. T6 quita el campo y desde ahí el punto General nace con un UUID propio.
- **La ola 2 es secuencial (T8 → T9).** Las dos tocan el resolver tal como lo usa `apps/api/tests/test_flujo.py:97`, y en paralelo la segunda integración rompería la suite.
- **Ola 1 se parte en dos tramos.** Si `sitios` borrara `Sitio.qr_codigo` antes de que `visitas` deje de compararlo, la suite queda en rojo y `worktree-integrar.sh` rechaza el merge. Por eso:
  - T3 crea los modelos, copia los QR y pasa `qr.py`, `regenerar_qr`, el resolver y el admin al punto, sin quitar los campos;
  - T6, después de visitas (T5), quita los campos de `Sitio` y suma `estado_revision`, que necesita `Revision`.
- **El comando `cerrar_visitas_abiertas` queda en la ola 1 (T5)**, como pidió el usuario; la propuesta lo ponía en la 2. `VISITA_ABIERTA_MAXIMO_HORAS` lo agrega el principal en T1, porque los settings son suyos.
- **En la ola 1, `POST visitas/` conserva su contrato** con una envoltura (abrir → revisión en el punto del QR → cerrar), para que sus 18 tests sigan valiendo hasta que T9 lo elimine y los reemplace por equivalentes.
- **`RecorridoTests.test_administrador_recorre_el_panel` ya existe** y un `[test]` del plan tiene que ser nuevo: T15 lo adapta y suma `test_administrador_recorre_puntos_y_planos`.
- **El grep de `qr_codigo` en `Sitio`** se reemplaza por un `[cmd]` que inspecciona `Sitio._meta`. El `grep -v PuntoControl` no excluye la línea del campo de `PuntoControl`.
- **El flujo end-to-end vive en `apps.visitas.tests.test_api.FlujoRevisionesTests`** (T9), como dice el criterio. `apps/api/tests/test_flujo.py` se adapta en T9, porque al quitar `POST visitas/` se rompe en ese worktree. T10 (principal) solo regenera el contrato.
- **`cargar_demo` no existe y se crea** en `apps/panel/management/commands/`.

**Excepciones de propiedad** (el `juez-plan` las ve declaradas; ninguna corre en paralelo con el dueño):
1. T5 (visitas) toca:
   - `apps/panel/mapa.py`, solo `visitas__realizada_en` → `visitas__cerrada_en`;
   - `apps/proyectos/panel_views.py` y `apps/proyectos/templates/proyectos/panel/ficha.html`, para el prefetch de revisiones;
   - `apps/servicios/panel_forms.py`, para que `clave_en_uso` mire también `Revision.datos`;
   - los tests que construyen visitas con evidencia: `apps/api/tests/test_flujo.py`, `apps/panel/tests/test_{mapa,recorrido,tablero}.py`, `apps/proyectos/tests/test_panel.py`, `apps/servicios/tests/test_panel.py` y `apps/sitios/tests/test_api.py`.
2. (sin uso: `apps/web/tests/test_rutas.py` no lee `sitio.qr_codigo`)
3. T8 (sitios API) toca `apps/api/tests/test_flujo.py`, solo la clave del esquema del resolver. Después T9 (visitas API) toca `apps/api/tests/test_flujo.py` y `apps/api/tests/test_schema.py`. Son secuenciales.
4. T12 (visitas panel) toca `apps/proyectos/panel_views.py`, `apps/proyectos/templates/proyectos/panel/ficha.html` y `apps/proyectos/tests/test_panel.py`.
5. T13 es la subtarea transversal de `apps/panel` en este plan, y además agrega una línea a `apps/panel/urls.py`, que es del principal: `sitios/<int:pk>/estado/`, nombre `panel:estado_sitio`, antes del `include("sitios/")`. La alternativa sin excepción obliga a secuenciar T13 → T11 o a dejar el test sin URL.
6. T15 (ola 4) escribe `apps/panel/management/**` y `apps/panel/tests/{test_cargar_demo,test_recorrido}.py`, con T13 ya integrada.

Las excepciones 1 y 3 a 6 tocan archivos de otro dueño, siempre sin que corran en paralelo con él. **Las aprueba explícitamente el usuario al aprobar el plan.** El `juez-plan` las marcó como bloqueantes según la tabla de propiedad.

## Contrato entre subtareas (fijo)

- **Modelos (T3, T5):**
  - `PuntoControl` y `Plano` en `apps/sitios/models.py`, con `related_name="puntos"` y `"planos"` desde `Sitio`. `Revision` en `apps/visitas/models.py`, con `related_name="revisiones"` desde `Visita` y desde `PuntoControl`.
  - `Foto.revision` y `ProductoAplicado.revision` llevan `related_name` `"fotos"` y `"productos"`.
  - `Visita.Estado.ABIERTA = "abierta"`, `Visita.Cierre` ∈ {`empleado`, `sistema`, `administrador`}, y `Visita.realizada_en` es una propiedad que devuelve `cerrada_en`.
- **Servicios de visitas (T5):** firmas sin argumentos posicionales.
  - `abrir_visita(*, empleado, proyecto) -> (visita, creada)`
  - `registrar_revision(*, visita, empleado, qr_codigo, cliente_uuid, realizada_en, latitud, longitud, precision_m, datos, productos_aplicados, fotos, observaciones="", incidencia=False, incidencia_detalle="") -> Revision`
  - `cerrar_visita(visita, *, quien, cierre, datos=None, observaciones=None, incidencia=None, incidencia_detalle=None) -> Visita`
  - `registrar_visita_manual(*, proyecto, empleado, administrador, motivo, realizada_en, puntos, datos, productos_aplicados, fotos, pendiente=None, confirmar_atraso=False, …)`
  - `RevisionDuplicada(Exception)` con `.revision`.
- **Estado (T6), en `apps/sitios/estado.py`:**
  - `estado_revision(punto, proyecto) -> str`;
  - `estados_de_puntos(puntos) -> dict[int, str]`, con un número constante de consultas;
  - `peor_estado_punto(estados)`;
  - `EstadoPunto` (TextChoices: `al_dia`, `proxima`, `vencida`, `sin_revisar`) y `GRAVEDAD_PUNTO`.
- **Parcial de estado (T13 → T11):** `GET /panel/sitios/<pk>/estado/` (`panel:estado_sitio`) devuelve `<ul id="estado-puntos">` con un `<li data-punto="<id>" data-estado="<estado>" data-x="<x|vacío>" data-y="<y|vacío>" data-plano="<id|vacío>">` por punto activo. El editor del plano (T11) recolorea sus marcadores en `htmx:afterSwap` leyendo esos atributos. La ficha enlaza la URL con `{% url 'panel:estado_sitio' sitio.pk as url_estado %}`.
- **API (T8, T9):**
  - `POST qr/<uuid>/resolver/` devuelve `{punto: {id, nombre, sector, plano|null}, sitio, cliente, proyectos: [{id, titulo, tipo_servicio, esquema_punto, esquema_visita, visita_pendiente_propia, visita_abierta_propia}]}`.
  - `plano` es `{id, nombre, url, ancho_px, alto_px, puntos: [{id, nombre, x, y, estado}]}`.
  - Rutas nuevas: `planos/<int:pk>/imagen/` (`api:sitios:plano-imagen`), `me/puntos/` (`api:sitios:mis-puntos`), `visitas/abrir/` (`api:visitas:abrir`), `revisiones/` (`api:visitas:revision`) y `visitas/<int:pk>/cerrar/` (`api:visitas:cerrar`).

## Olas

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1 (principal: dependencia y setting), T2 (servicios) ∥ T3 (sitios: modelos), T4 (integración), T5 (visitas), T6 (sitios: quita campos y estado), T7 (integración) | servicios, sitios (0004), visitas, sitios (0005) |
| 2 | T8 (sitios API) → T9 (visitas API), T10 (integración y contrato) | — |
| 3 | T11 (sitios panel) ∥ T12 (visitas panel) ∥ T13 (panel: estado y mapa), T14 (integración) | — |
| 4 | T15 (demo y recorrido) ∥ T16 (documentación), T17 (integración final) | — |

Ninguna subtarea crea migraciones en paralelo con otra de la misma app. T5 y T6 son secuenciales: T6 ramifica después de integrar T5.

## Subtareas

### T1 — Preparación (principal): `pypdfium2` y `VISITA_ABIERTA_MAXIMO_HORAS`

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `requirements.txt`, `config/settings/base.py`, `.env.example`
- **No puede tocar**: `docs/planes/`, `apps/`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § Variables de entorno
- **Worktree**: no (principal, en `plan/puntos-control`, antes de crear los worktrees de T2 y T3)
- **Ruta**: inline · Evidencia: criterios · Commit: `T1: …`
- **Presupuesto**: 30 líneas agregadas
- **Qué hacer**: agregar `pypdfium2` a `requirements.txt` e instalarlo en el venv. Agregar `VISITA_ABIERTA_MAXIMO_HORAS = 16` en `config/settings/base.py`, junto a `ATRASO_MAXIMO_HORAS`, con un comentario.
- **Criterios**:
  - `[grep-1]` `grep -n "^pypdfium2" requirements.txt`
  - `[cmd]` `./venv/Scripts/python.exe -c "import pypdfium2"`
  - `[grep-1]` `grep -n "VISITA_ABIERTA_MAXIMO_HORAS = 16" config/settings/base.py`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 30 --subtarea T1`

### T2 — Servicios: ámbito de `CampoPlanilla`

- **Ola**: 1
- **Depende de**: T1
- **Puede tocar**: `apps/servicios/models.py`, `apps/servicios/migrations/0003_*.py` (generada), `apps/servicios/panel_forms.py`, `apps/servicios/panel_views.py`, `apps/servicios/templates/servicios/panel/*.html`, `apps/servicios/admin.py`, `apps/servicios/tests/*`
- **No puede tocar**: `docs/planes/`, `config/`, otras apps
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § 2.8 Migration Best Practices
- **Worktree**: sí
- **Ruta**: delegada (implementador) · Evidencia: informe + verificador · Commit: `T2: …`
- **Presupuesto**: 250 líneas agregadas
- **Qué hacer**:
  - `CampoPlanilla.ambito` (choices `punto`, `visita`; default `punto`) y migración. Los campos existentes quedan en `punto` por el default.
  - `TipoServicio.esquema_planilla(ambito="punto")` filtra por ámbito y sigue usando el prefetch.
  - En el panel, el formulario de campo muestra `ambito`; como `clave` y `tipo`, queda fijo si una visita usó la clave.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.servicios.tests.test_models.AmbitoTests.test_esquema_filtra_por_ambito --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.servicios.tests.test_panel.PlanillaPanelTests.test_ambito_fijo_si_una_visita_uso_la_clave --keepdb`
  - `[grep-1]` `grep -n "ambito" apps/servicios/models.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.servicios --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 --subtarea T2`

### T3 — Sitios: `PuntoControl`, `Plano`, QR por punto y conversión de planos

- **Ola**: 1
- **Depende de**: T1
- **Puede tocar**: `apps/sitios/models.py`, `apps/sitios/migrations/0004_*.py`, `apps/sitios/services.py`, `apps/sitios/qr.py`, `apps/sitios/planos.py` (nuevo), `apps/sitios/admin.py`, `apps/sitios/templates/admin/sitios/**`, `apps/sitios/api_views.py`, `apps/sitios/panel_views.py`, `apps/sitios/templates/sitios/panel/ficha.html`, `apps/sitios/tests/*`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/visitas/`, otras apps
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § 2.8 Migration Best Practices; `.agents/skills/django-security/SKILL.md` § File Upload Security
- **Worktree**: sí
- **Ruta**: delegada (implementador) · Evidencia: informe + verificador · Commit: `T3: …`
- **Presupuesto**: 1000 líneas agregadas
- **Qué hacer**:
  - **Modelos y migración `0004`**. `Plano` y `PuntoControl` según la propuesta (§ Modelo), con `HistoricalRecords` en ambos; `ubicacion_propuesta` sale del historial. `PuntoControl.clean()` rechaza un punto activo con sitio inactivo y un `plano` de otro sitio. `Sitio.save()` desactiva los puntos activos al desactivarse el sitio.
  - **`RunPython` con `reverse_code`** (el docstring justifica la migración escrita a mano): crea el punto "General" (`orden=0`) de cada sitio con su `qr_codigo` y su `qr_impreso_el`. Los campos de `Sitio` **no** se quitan acá (los quita T6).
  - **Transición del QR**: `Sitio.save()`, al crear, también crea el punto "General" con `qr_codigo = sitio.qr_codigo`, y `regenerar_qr` del punto General copia el código nuevo a `Sitio.qr_codigo` (ver "Cambios respecto del pedido").
  - **Código que pasa al punto**:
    - `qr.py` recibe un punto: el contenido sigue siendo `SITE_URL + /q/<uuid>/`, y la etiqueta lleva el nombre del sitio y el del punto.
    - `services.regenerar_qr(punto)` y `regenerar_qr_lote(puntos)`, con tope de 20.
    - `ResolverQRView` busca `PuntoControl` activo con sitio y cliente activos; la respuesta conserva su forma hasta T8.
    - El admin suma `PuntoControlAdmin` con la acción de regenerar y el bloqueo del revert. `SitioAdmin` pierde esa acción.
    - La ficha y la vista PNG del panel usan el punto General hasta T11.
  - **`planos.py`**:
    - `procesar_plano(archivo) -> (ContentFile, ancho, alto)` acepta JPG, PNG y PDF de hasta 20 MB. Para el PDF usa `pypdfium2`: primera página, nada de cifrados ni vacíos.
    - Limita los píxeles de entrada contra bombas, reduce a 4000 px el lado mayor, quita los metadatos y guarda PNG. Cualquier otro formato da `ValidationError`.
    - `Plano.save()` lo aplica y fija `ancho_px`/`alto_px`.
  - **Tests de migración** con `MigrationExecutor` en un `TransactionTestCase` (`apps/sitios/tests/test_migraciones.py`): de `sitios 0003` a `0004`, y vuelta a la última.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_migraciones.MigracionPuntosTests.test_cada_sitio_recibe_punto_general_con_su_qr --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_models.PuntoControlTests.test_qr_unico_y_sitio_inactivo_desactiva_puntos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_planos.PlanoTests.test_pdf_se_convierte_a_imagen_y_otros_formatos_se_rechazan --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_planos.PlanoTests.test_imagen_grande_se_reduce_a_4000_px --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_services.RegenerarQrPuntoTests.test_regenera_solo_el_punto_y_respeta_tope --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api.ResolverQRTests.test_qr_de_punto_inactivo_da_404 --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 1000 --subtarea T3`

### T4 — Integración ola 1a (principal)

- **Ola**: 1 (después de verificar T2 y T3)
- **Depende de**: T2, T3
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/puntos-control` de cada worktree.
  2. Desde la raíz, `bash .claude/hooks/worktree-integrar.sh puntos-control T2 plan/puntos-control apps/servicios` y `… T3 plan/puntos-control apps/sitios`.
  3. Crear `worktrees/puntos-control-T5` con `bash .claude/hooks/worktree-crear.sh puntos-control T5 plan/puntos-control`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/puntos-control | grep -q "T2: integra puntos-control-T2"`
  - `[cmd]` `git log --oneline plan/puntos-control | grep -q "T3: integra puntos-control-T3"`

### T5 — Visitas: jornada, `Revision`, migración de datos, servicios y comando

- **Ola**: 1
- **Depende de**: T4
- **Puede tocar**:
  - `apps/visitas/**` (incluidas las migraciones `0005_*`… y `management/commands/cerrar_visitas_abiertas.py`);
  - excepción 1: `apps/panel/mapa.py`, `apps/proyectos/panel_views.py`, `apps/proyectos/templates/proyectos/panel/ficha.html` y `apps/servicios/panel_forms.py`;
  - excepción 1, tests: `apps/api/tests/test_flujo.py`, `apps/panel/tests/test_mapa.py`, `apps/panel/tests/test_recorrido.py`, `apps/panel/tests/test_tablero.py`, `apps/proyectos/tests/test_panel.py`, `apps/servicios/tests/test_panel.py` y `apps/sitios/tests/test_api.py`.
- **No puede tocar**: `docs/planes/`, `config/`, `apps/sitios/` (salvo `tests/test_api.py`), `apps/api/` (salvo los tests nombrados)
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § 2.8 Migration Best Practices; `.agents/skills/django-patterns/SKILL.md` § services
- **Worktree**: sí
- **Ruta**: delegada (implementador) · Evidencia: informe + verificador · Commit: `T5: …`
- **Presupuesto**: 2800 líneas agregadas. Es grande porque no se puede partir sin dejar la suite en rojo entre partes, e incluye las migraciones generadas y la reescritura de unos 140 tests.
- **Qué hacer**:
  - **Modelos**:
    - `Revision` según la propuesta, con historial (decisión 9).
    - `Foto` y `ProductoAplicado` cuelgan de `revision`.
    - `Visita` suma `abierta_en`, `cierre` y el estado `abierta`; renombra `realizada_en` → `cerrada_en` con `RenameField`, para conservar los datos, y deja `realizada_en` como propiedad.
    - `Visita` pierde los campos que pasan a `Revision`.
    - `clean()`: una pendiente no tiene revisiones.
  - **Migraciones**: esquema más un `RunPython` con `reverse_code` que, por cada visita realizada:
    - crea la revisión "General" en el punto `orden=0` del sitio, con coordenadas, `cliente_uuid`, `recibida_en`, `realizada_en`, `datos` y `esquema_planilla`;
    - reasigna fotos y productos;
    - fija `abierta_en = cerrada_en` y `cierre` (`empleado` si `origen=app`, `administrador` si `manual`);
    - deja `Visita.datos = {}` y `Visita.esquema_planilla = []`.
  - **Servicios** con las firmas del contrato:
    - `registrar_revision` valida: QR de un punto activo del sitio del proyecto; visita abierta del mismo empleado; coordenadas; de 1 a `MAX_FOTOS` fotos; atraso `ATRASO_MAXIMO_HORAS` y tolerancia futura; `cliente_uuid` idempotente (`RevisionDuplicada`). También aplica la ubicación propuesta (decisión 2) y guarda la planilla de ámbito `punto`.
    - `cerrar_visita` lleva la actualización del proyecto que hoy hace `registrar_visita_realizada`: bloqueo, regla "solo la más reciente", planilla de ámbito `visita` y decisión 4.
    - `registrar_visita_manual` trabaja por puntos (decisión 6).
    - `registrar_visita_desde_app` queda como envoltura del contrato viejo hasta T9.
  - **Comando** `cerrar_visitas_abiertas`: cierra con `cierre=sistema` las abiertas desde hace más de `settings.VISITA_ABIERTA_MAXIMO_HORAS`.
  - **Admin**: inlines de revisión de solo lectura en visitas no pendientes.
  - **Panel de visitas**: el formulario manual suma `puntos` (los puntos activos del sitio, al menos uno).
  - **Fuera de visitas**: mínimo para que la suite quede en verde (excepción 1).
  - **QR del punto, no del sitio**: el servicio y todos los tests de `apps/visitas` y `apps/api` usan el `qr_codigo` del punto, nunca `sitio.qr_codigo`. Es condición para T6.
  - **Tests**: ninguno se borra sin un reemplazo equivalente.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_migraciones.MigracionRevisionesTests.test_fotos_y_productos_pasan_a_revision_general --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.CicloVisitaTests.test_abrir_revisar_cerrar_actualiza_proyecto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.CicloVisitaTests.test_revision_exige_punto_activo_coordenadas_y_foto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.CicloVisitaTests.test_mismo_punto_dos_veces_la_ultima_manda --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.CicloVisitaTests.test_revision_propone_ubicacion_solo_sin_coordenadas_y_precisa --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.CicloVisitaTests.test_qr_de_otro_sitio_se_rechaza --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.ManualPorPuntosTests.test_crea_una_revision_por_punto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_comandos.CerrarAbiertasTests.test_cierra_por_sistema_pasado_el_maximo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_comandos.CerrarAbiertasTests.test_sin_revisiones_vuelve_a_pendiente_o_se_cancela --keepdb`
  - `[grep-0]` `grep -rn "sitio\.qr_codigo\|sitio__qr_codigo" apps/visitas apps/api apps/panel apps/proyectos apps/servicios --include=*.py --exclude-dir=migrations`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 2800 --subtarea T5`

### T6 — Sitios: quitar el QR de `Sitio` y calcular el estado por punto

- **Ola**: 1
- **Depende de**: T5 integrada (pasos de T7)
- **Puede tocar**: `apps/sitios/**` (migración `0005_*`, `estado.py` nuevo; las migraciones `0001`–`0004` no se editan)
- **No puede tocar**: `docs/planes/`, `config/`, `apps/visitas/`, otras apps
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § 2.8 Migration Best Practices; `.agents/skills/python-performance-optimization/SKILL.md` § consultas
- **Worktree**: sí
- **Ruta**: delegada (implementador) · Evidencia: informe + verificador · Commit: `T6: …`
- **Presupuesto**: 500 líneas agregadas
- **Qué hacer**:
  - **Migración `0005`**: quita `qr_codigo` y `qr_impreso_el` de `Sitio` y de su historial. Tiene que ser reversible sobre la base vacía de los tests, y el test de migración de T3 sigue en verde.
  - Se quitan del formulario y de las plantillas del panel. `qr_impreso_el` se edita en el punto en T11.
  - El punto General de un sitio nuevo pasa a tener un UUID propio, y se quita la copia a `Sitio.qr_codigo` al regenerar.
  - **`estado.py`**, según el contrato y la decisión 5. Importa `UMBRAL_PROXIMA_DIAS` de `apps/proyectos/models.py`, no lo duplica. `estados_de_puntos` resuelve la última revisión por (punto, proyecto) con una agregación, en un número de consultas que no depende de cuántos puntos haya.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_models.EstadoRevisionTests.test_vencida_proxima_al_dia_sin_revisar --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_models.EstadoRevisionTests.test_estados_de_puntos_consultas_constantes --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_models.PuntoControlTests.test_sitio_nuevo_recibe_punto_general_con_qr_propio --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py shell -c "import sys; from apps.sitios.models import Sitio; sys.exit(int(any(f.name in ('qr_codigo', 'qr_impreso_el') for f in Sitio._meta.get_fields()) or any(f.name in ('qr_codigo', 'qr_impreso_el') for f in Sitio.history.model._meta.get_fields())))"`
  - `[grep-0]` `grep -rn "sitio\.qr_codigo\|sitio__qr_codigo" apps --include=*.py --exclude-dir=migrations --exclude=test_migraciones.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 500 --subtarea T6`

### T7 — Integración ola 1 (principal)

- **Ola**: 1 (T5 y T6, en secuencia)
- **Depende de**: T5, T6
- **Pasos**:
  1. Verificar T5 y revisar `cambios.sh`. Integrar con `bash .claude/hooks/worktree-integrar.sh puntos-control T5 plan/puntos-control apps/visitas apps/panel/mapa.py apps/proyectos apps/servicios/panel_forms.py apps/api/tests apps/panel/tests apps/servicios/tests apps/sitios/tests/test_api.py`.
  2. Crear el worktree de T6 desde `plan/puntos-control`, verificarlo e integrarlo con `… T6 plan/puntos-control apps/sitios`.
  3. Correr `auditor-seguridad` sobre la ola 1: migraciones de datos, QR por punto, planos y revisiones.
  4. Crear el worktree de T8.
- **Presupuesto**: no aplica (solo merges y commits `registro:`); si el principal hace commits `T7:` de ajuste, `bash .claude/hooks/presupuesto.sh . '<commit_base>' 80 --subtarea T7`
- **Criterios**:
  - `[cmd]` `git log --oneline plan/puntos-control | grep -q "T5: integra puntos-control-T5"`
  - `[cmd]` `git log --oneline plan/puntos-control | grep -q "T6: integra puntos-control-T6"`

### T8 — Sitios API: resolver por punto, imagen del plano y `me/puntos/`

- **Ola**: 2
- **Depende de**: T7
- **Puede tocar**: `apps/sitios/api_views.py`, `apps/sitios/api_urls.py`, `apps/sitios/serializers.py`, `apps/sitios/tests/test_api.py`; excepción 3: `apps/api/tests/test_flujo.py` (solo la clave del esquema del resolver)
- **No puede tocar**: `docs/planes/`, `config/`, `apps/api/` (salvo la excepción), `apps/visitas/`, `docs/api/`
- **Skill a leer antes**: `.agents/skills/django-rest-framework/SKILL.md` § permisos y serializers; `.agents/skills/api-security-best-practices/SKILL.md` § autorización
- **Worktree**: sí
- **Ruta**: delegada (implementador) · Evidencia: informe + verificador · Commit: `T8: …`
- **Presupuesto**: 700 líneas agregadas
- **Qué hacer**:
  - **Resolver**: devuelve la forma del contrato, con los estados de `estados_de_puntos` y `prefetch_related("tipo_servicio__campos")` (P-panel-7 en el resolver). La `description` menciona el cliente inactivo (P-saneamiento-5).
  - **`GET planos/<pk>/imagen/`**: `EsEmpleado | EsAdministrador`. El empleado necesita una visita propia pendiente o abierta en un proyecto de ese sitio; si no, 404. El plano tiene que estar activo. Responde `FileResponse` PNG con `private, no-store` y `nosniff`.
  - **`GET me/puntos/?sitio=`**: puntos activos con lat/lng de los sitios donde el empleado tiene visitas pendientes o abiertas, con su estado.
  - Todo con `extend_schema`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api.ResolverQRTests.test_devuelve_punto_plano_y_visita_abierta --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api.PlanoApiTests.test_imagen_solo_con_visita_en_el_sitio --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api.MisPuntosTests.test_solo_sitios_con_visita_asignada_o_abierta --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 700 --subtarea T8`

### T9 — Visitas API: abrir, revisiones, cerrar, `me/visitas` e historial

- **Ola**: 2
- **Depende de**: T8 integrada (paso 1 de T10)
- **Puede tocar**: `apps/visitas/api_views.py`, `apps/visitas/api_urls.py`, `apps/visitas/serializers.py`, `apps/visitas/services.py` (solo quitar la envoltura `registrar_visita_desde_app`), `apps/visitas/tests/test_api.py`, `apps/visitas/tests/test_atraso.py`, `apps/visitas/tests/test_services.py`; excepción 3: `apps/api/tests/test_flujo.py`, `apps/api/tests/test_schema.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/sitios/`, `docs/api/`
- **Skill a leer antes**: `.agents/skills/django-rest-framework/SKILL.md` § serializers y vistas; `.agents/skills/api-security-best-practices/SKILL.md` § autorización
- **Worktree**: sí
- **Ruta**: delegada (implementador) · Evidencia: informe + verificador · Commit: `T9: …`
- **Presupuesto**: 1200 líneas agregadas
- **Qué hacer**:
  - **Rutas nuevas**: `POST visitas/abrir/` (201 si la crea, 200 si ya existía), `POST revisiones/` y `POST visitas/<pk>/cerrar/`. La de revisiones es multipart con `qr_codigo`, conserva el 413 y el 409 de idempotencia, y el chequeo de atraso se saltea si el `cliente_uuid` existe.
  - **Rutas que cambian**: `GET me/visitas/` lista pendientes y abiertas con `estado`. `GET me/historial/` lista las visitas realizadas con sus revisiones (punto, fecha, planilla, productos, fotos).
  - **`FotoView`** comprueba `foto.revision.visita.empleado`.
  - **Se elimina `POST visitas/`** con su envoltura, y sus tests se reemplazan por equivalentes sobre revisiones (atraso, idempotencia, 413, foto obligatoria, QR inválido).
  - El scope de throttle es `crear_visita` (decisión 8). Todo con `extend_schema`, incluidas las respuestas 400, 409 y 413.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api.FlujoRevisionesTests.test_abrir_tres_revisiones_cerrar --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api.FlujoRevisionesTests.test_post_visitas_ya_no_existe --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api.FlujoRevisionesTests.test_revision_en_visita_ajena_o_cerrada_se_rechaza --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api.FotoTests.test_foto_de_revision_ajena_da_403 --keepdb`
  - `[grep-0]` `grep -rn 'path("visitas/", ' apps/visitas/api_urls.py`
  - `[grep-0]` `grep -n "def registrar_visita_desde_app" apps/visitas/services.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 1200 --subtarea T9`

### T10 — Integración ola 2 y contrato (principal)

- **Ola**: 2 (T8 y T9 en secuencia)
- **Depende de**: T8, T9
- **Pasos**:
  1. Verificar T8, revisar `cambios.sh` e integrarlo (`apps/sitios apps/api/tests/test_flujo.py`). Crear el worktree de T9 desde `plan/puntos-control`, verificarlo e integrarlo (`apps/visitas apps/api/tests`).
  2. Regenerar `docs/api/openapi-v1.yaml` con `manage.py spectacular --validate --file docs/api/openapi-v1.yaml` y commitearlo como `T10: contrato openapi`.
  3. Correr `auditor-seguridad` sobre la ola 2: permisos de imagen y puntos, `qr_codigo` en revisiones, idempotencia.
  4. Crear los worktrees de T11, T12 y T13.
- **Presupuesto**: `bash .claude/hooks/presupuesto.sh . '<commit_base>' 1500 --subtarea T10` (casi todo es el YAML generado)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/puntos-control | grep -q "T8: integra puntos-control-T8"`
  - `[cmd]` `git log --oneline plan/puntos-control | grep -q "T9: integra puntos-control-T9"`
  - `[cmd]` `T=$(mktemp) && PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file "$(cygpath -w "$T")" && diff -q --strip-trailing-cr "$T" docs/api/openapi-v1.yaml; r=$?; rm -f "$T"; exit $r`
  - `[grep-1]` `grep -n "/api/v1/revisiones/" docs/api/openapi-v1.yaml`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 1500 --subtarea T10`

### T11 — Sitios panel: puntos, mapa de puntos, planos con editor y QR por punto

- **Ola**: 3
- **Depende de**: T10
- **Puede tocar**: `apps/sitios/panel_views.py`, `apps/sitios/panel_urls.py`, `apps/sitios/panel_forms.py`, `apps/sitios/qr.py`, `apps/sitios/services.py`, `apps/sitios/templates/sitios/panel/**`, `apps/sitios/static/sitios/**`, `apps/sitios/tests/test_panel.py`
- **No puede tocar**: `docs/planes/`, `config/`, `templates/`, `static/`, `apps/panel/`, `apps/sitios/models.py`, `apps/sitios/migrations/`, otras apps
- **Skill a leer antes**: `.agents/skills/django-patterns/SKILL.md` § vistas y formularios; `.agents/skills/frontend-design/SKILL.md` (lo que aplique al panel); `docs/02-diseno.md` § panel
- **Worktree**: sí
- **Ruta**: delegada (implementador) · Evidencia: informe + verificador · Commit: `T11: …`
- **Presupuesto**: 1300 líneas agregadas
- **Qué hacer**:
  - **Ficha del sitio** con pestañas:
    - **Mapa de puntos**: Leaflet con teselas OSM y `csp_update`. Un clic fija lat/lng del punto elegido por POST con CSRF. Botones para aceptar o descartar `ubicacion_propuesta`.
    - **Planos**: subir (`procesar_plano`) y editor Leaflet `CRS.Simple` con la imagen servida por una vista del panel autenticada. Los marcadores son arrastrables y guardan `x,y` (fracción 0–1) con un POST HTMX. Se puede dar de alta un punto haciendo clic en el plano.
    - **Listado de puntos** con semáforo, alta, edición (`qr_impreso_el` incluido) y desactivación.
  - **QR**: PNG por punto con el nombre del punto y el sector (`qr.py`), y regenerar por punto con confirmación.
  - **Sondeo**: el contenedor de estado usa `hx-get="{{ url_estado }}" hx-trigger="every 5s"` más `sondeo.js` (decisión 10), y el editor recolorea los marcadores en `htmx:afterSwap` (contrato).
  - JS en `apps/sitios/static/sitios/`, sin estilos ni scripts en línea (CSP).
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel.PlanoPanelTests.test_arrastrar_marcador_guarda_xy --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel.PlanoPanelTests.test_subir_pdf_crea_plano_y_rechaza_otro_formato --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel.PuntoPanelTests.test_aceptar_ubicacion_propuesta --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel.PuntoPanelTests.test_qr_png_por_punto_y_regenerar --keepdb`
  - `[grep-1]` `grep -rn 'hx-trigger="every 5s' apps/sitios/templates/sitios/panel/`
  - `[grep-1]` `grep -rn "CRS.Simple" apps/sitios/static/sitios/`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 1300 --subtarea T11`

### T12 — Visitas panel: revisiones en fichas, manual por puntos y estado abierta

- **Ola**: 3
- **Depende de**: T10
- **Puede tocar**: `apps/visitas/panel_views.py`, `apps/visitas/panel_urls.py`, `apps/visitas/panel_forms.py`, `apps/visitas/templates/visitas/panel/**`, `apps/visitas/tests/test_panel.py`; excepción 4: `apps/proyectos/panel_views.py`, `apps/proyectos/templates/proyectos/panel/ficha.html`, `apps/proyectos/tests/test_panel.py`
- **No puede tocar**: `docs/planes/`, `config/`, `templates/`, `static/`, `apps/panel/`, `apps/sitios/`, modelos y migraciones
- **Skill a leer antes**: `.agents/skills/django-patterns/SKILL.md` § vistas y formularios
- **Worktree**: sí
- **Ruta**: delegada (implementador) · Evidencia: informe + verificador · Commit: `T12: …`
- **Presupuesto**: 700 líneas agregadas
- **Qué hacer**:
  - Fichas:
    - la ficha de visita muestra sus revisiones (punto, fecha, planilla por punto, productos, fotos) y la planilla de ámbito visita;
    - la ficha de proyecto, una línea de tiempo por visita con sus revisiones desplegables (`<details>`), con un número constante de consultas.
  - La visita manual elige los puntos revisados con casillas.
  - El listado filtra y muestra el estado `abierta`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel.FichaVisitaTests.test_muestra_revisiones_por_punto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel.ManualTests.test_manual_elige_puntos_revisados --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel.ListadoVisitasTests.test_filtra_abiertas --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.proyectos.tests.test_panel.ProyectoPanelTests.test_ficha_lista_revisiones_consultas_constantes --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas apps.proyectos --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 700 --subtarea T12`

### T13 — Panel: vista de estado por sitio y mapa por peor estado de puntos

- **Ola**: 3
- **Depende de**: T10
- **Puede tocar**: `apps/panel/estado.py` (nuevo), `apps/panel/mapa.py`, `apps/panel/views.py`, `apps/panel/templates/panel/**`, `apps/panel/static/panel/**`, `apps/panel/templatetags/panel_ui.py`, `apps/panel/tests/test_estado.py`, `apps/panel/tests/test_mapa.py`, `apps/panel/tests/test_diseno.py`; excepción 5: `apps/panel/urls.py` (una línea)
- **No puede tocar**: `docs/planes/`, `config/`, `templates/`, `static/`, `apps/sitios/`, `apps/visitas/`
- **Skill a leer antes**: `.agents/skills/python-performance-optimization/SKILL.md` § consultas; `.agents/skills/django-patterns/SKILL.md` § vistas
- **Worktree**: sí
- **Ruta**: delegada (implementador) · Evidencia: informe + verificador · Commit: `T13: …`
- **Presupuesto**: 600 líneas agregadas
- **Qué hacer**:
  - **Vista `panel:estado_sitio`** (solo administrador): devuelve el parcial del contrato a partir de `estados_de_puntos`, con un número de consultas que no depende de cuántos puntos haya. Es el único punto de transporte, para poder pasar a SSE más adelante.
  - **Mapa**: el color del sitio es el peor estado de sus puntos (`GRAVEDAD_PUNTO`), y el filtro `estado` acepta los valores de `EstadoPunto`. La prueba de consultas constantes sigue en verde.
  - **`tono_estado`** suma `sin_revisar` → `neutral` y `abierta` → `warn`.
  - **Sin duplicados**: `apps/panel/mapa.py` deja de tener su propio `GRAVEDAD` y su `peor_estado`, y usa los de `apps/sitios/estado.py`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_estado.EstadoSitioTests.test_parcial_refleja_revision_reciente --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_estado.EstadoSitioTests.test_consultas_constantes --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_estado.EstadoSitioTests.test_empleado_recibe_403 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_mapa.MapaTests.test_color_es_peor_estado_de_puntos --keepdb`
  - `[grep-0]` `grep -n "def peor_estado\|^GRAVEDAD" apps/panel/mapa.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 600 --subtarea T13`

### T14 — Integración ola 3 (principal)

- **Ola**: 3 (después de verificar T11, T12 y T13)
- **Depende de**: T11, T12, T13
- **Pasos**:
  1. Revisar `cambios.sh`. Integrar T13 primero (`apps/panel`, porque trae la URL), después T11 (`apps/sitios`) y T12 (`apps/visitas apps/proyectos`).
  2. Comprobar en `runserver` que la ficha sondea y el editor arrastra.
  3. Correr `auditor-seguridad` sobre la ola 3: subida de planos desde el panel, servido de la imagen, CSP y POST de coordenadas.
  4. Crear los worktrees de T15 y T16.
- **Presupuesto**: no aplica (solo merges y commits `registro:`); si hay commits `T14:` de ajuste, `bash .claude/hooks/presupuesto.sh . '<commit_base>' 80 --subtarea T14`
- **Criterios**:
  - `[cmd]` `git log --oneline plan/puntos-control | grep -q "T11: integra puntos-control-T11"`
  - `[cmd]` `git log --oneline plan/puntos-control | grep -q "T12: integra puntos-control-T12"`
  - `[cmd]` `git log --oneline plan/puntos-control | grep -q "T13: integra puntos-control-T13"`

### T15 — `cargar_demo` con puntos y planos, y recorrido del panel

- **Ola**: 4
- **Depende de**: T14
- **Puede tocar**: `apps/panel/management/**` (nuevo), `apps/panel/tests/test_cargar_demo.py` (nuevo), `apps/panel/tests/test_recorrido.py`
- **No puede tocar**: `docs/planes/`, `config/`, el resto de `apps/`
- **Skill a leer antes**: `.agents/skills/django-patterns/SKILL.md` § management commands
- **Worktree**: sí
- **Ruta**: delegada (implementador) · Evidencia: informe + verificador · Commit: `T15: …`
- **Presupuesto**: 600 líneas agregadas
- **Qué hacer**:
  - **`cargar_demo`**: idempotente y solo con `DEBUG`. Si `DEBUG` es falso, falla con `CommandError`. Crea:
    - clientes y sitios de ejemplo, sin datos reales inventados de empresas: nombres genéricos;
    - puntos con coordenadas;
    - un plano generado con Pillow por cada sitio de más de tres puntos, con los marcadores ubicados;
    - proyectos y visitas realizadas, con revisiones, fotos generadas y una visita abierta.
  - **Recorrido**: se adapta el existente y se suma uno nuevo que recorre ficha del sitio → puntos → plano (subir, mover marcador) → estado → visita manual por puntos → ficha de proyecto con revisiones.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_cargar_demo.CargarDemoTests.test_crea_puntos_plano_y_revisiones_idempotente --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_recorrido.RecorridoTests.test_administrador_recorre_puntos_y_planos --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_recorrido.RecorridoTests.test_administrador_recorre_el_panel --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 600 --subtarea T15`

### T16 — Documentación: modelo y convenciones

- **Ola**: 4
- **Depende de**: T14
- **Puede tocar**: `docs/01-modelo-y-arquitectura.md`, `.claude/skills/convenciones-proyecto/SKILL.md`
- **No puede tocar**: `docs/planes/`, `docs/decisiones.md`, `docs/bitacora.md`, código
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` completo; `docs/propuestas/2026-10-05-puntos-de-control.md`
- **Worktree**: sí
- **Ruta**: delegada (implementador) · Evidencia: informe + verificador · Commit: `T16: …`
- **Presupuesto**: 300 líneas agregadas
- **Qué hacer**:
  - En `docs/01`, reescribir:
    - el diagrama de §3;
    - §3.2: Sitio, más PuntoControl y Plano como §3.2.1 y §3.2.2;
    - §3.4: ámbito;
    - §3.6: Visita como jornada, más Revisión;
    - §3.7 y §3.8: cuelgan de Revisión;
    - §4.1 y §4.2: abrir, revisiones, cerrar, `me/puntos`, planos, sondeo y mapa.
  - En la versión del encabezado, citar el plan.
  - En `convenciones-proyecto`, actualizar la estructura de `sitios` y `visitas` y las reglas de dominio de las líneas 137–140 (revisión desde QR de un punto; `cerrar_visita` actualiza el proyecto).
- **Criterios**:
  - `[grep-1]` `grep -n "PuntoControl" docs/01-modelo-y-arquitectura.md`
  - `[grep-1]` `grep -n "visitas/abrir/" docs/01-modelo-y-arquitectura.md`
  - `[grep-0]` `grep -n "Un QR por sitio" docs/01-modelo-y-arquitectura.md`
  - `[grep-0]` `grep -n "multipart (JSON + fotos + geolocalización)" docs/01-modelo-y-arquitectura.md`
  - `[grep-1]` `grep -n "cerrar_visita" .claude/skills/convenciones-proyecto/SKILL.md`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 --subtarea T16`

### T17 — Integración final (principal)

- **Ola**: 4 (después de verificar T15 y T16)
- **Depende de**: T15, T16
- **Pasos**:
  1. Integrar T15 (`apps/panel`) y T16 (`docs/01-modelo-y-arquitectura.md .claude/skills/convenciones-proyecto/SKILL.md`).
  2. Escribir las decisiones de este plan en `### Decisiones` (debajo del corte).
  3. Correr `auditor-seguridad` sobre T15 (`cargar_demo`: protección con `DEBUG`, datos inventados y archivos generados).
  4. Correr `verificador` y `verificador-b` con `TODO`, y `refutador` si discrepan.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/puntos-control | grep -q "T15: integra puntos-control-T15"`
  - `[cmd]` `git log --oneline plan/puntos-control | grep -q "T16: integra puntos-control-T16"`

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `T=$(mktemp) && PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file "$(cygpath -w "$T")" && diff -q --strip-trailing-cr "$T" docs/api/openapi-v1.yaml; r=$?; rm -f "$T"; exit $r`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-05-puntos-control.md puntos-control`

## Registro de verificación

commit_base: 4e2c496

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
| T10 | pendiente |
| T11 | pendiente |
| T12 | pendiente |
| T13 | pendiente |
| T14 | pendiente |
| T15 | pendiente |
| T16 | pendiente |
| T17 | pendiente |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| 2026-10-05 | T1, T2, T3 | 6e87fa5 (raíz) · ec9d395 (T2) · c875441 (T3) | PASA 20/20 | verificador; contrato intacto |
| 2026-10-05 | T4 | 6e3faaf | PASA 2/2 | principal: criterios de integración; suite 393 OK en worktree-integrar |
| 2026-10-05 | T5 | b48bf5e | PASA 13/13 | verificador; integrada en 6cd1966 (suite 425 OK) |

## Pendientes que deja este plan

### Problemas

- P-puntos-control-1 [observación] T5 editó a mano `apps/visitas/migrations/0005_revision_y_jornada.py` para usar `RenameField` (`realizada_en` → `cerrada_en` en `visita` y `historicalvisita`): `makemigrations` no interactivo generaba quitar y agregar, y se perdían los datos. La convención solo admite a mano el `RunPython` justificado.
- P-puntos-control-2 [observación] El `reverse_code` de `visitas/0006` devuelve a la visita solo su primera revisión: es reversible sin pérdida para las visitas migradas (una revisión "General"), no para jornadas con varias revisiones.
- P-puntos-control-3 [observación] T5 quitó tests sin un reemplazo de nombre parecido porque el comportamiento ya no existe: pendiente con fotos o productos (`CrearVisitaTests.test_pendiente_con_*_crea_nueva_con_incidencia`, `ManualTests.test_pendiente_con_evidencia_se_rechaza`) y subida de fotos desde el admin (`test_foto_admin_*`, `test_imagen_invalida_da_error_de_formulario_no_500`). La actualización del proyecto la cubre `CicloVisitaTests.test_abrir_revisar_cerrar_actualiza_proyecto`.
- P-puntos-control-4 [menor] `cerrar_visita` suma el kwarg `cerrada_en=None` y `registrar_visita_manual` suma `datos_visita=None`, fuera de las firmas del contrato (los usan la carga manual y la envoltura de `POST visitas/`).
- P-puntos-control-5 [observación] `ubicacion_propuesta` guarda `{"latitud", "longitud", "precision_m", "revision"}` con decimales como texto; el panel (T11) lee esas claves.

### Decisiones

### Cierra
