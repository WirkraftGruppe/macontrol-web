# Plan: Robustez del panel
<!-- flujo: commit "docs(plan): robustez-panel" antes del primer subagente; hash en Registro (commit_base:); criterios congelados; T<n>: commits; verificador por T<n> y TODO; '<commit_base>' literal entre comillas simples; corte de congelado en ## Registro de verificación; congelado.sh; hook verificar_plan.py -->
<!-- aprobación: juez-plan 2026-10-08 (0 bloqueantes, 6 observaciones; 2 referencias de línea corregidas); usuario 2026-10-08 (con tres ajustes: frase de tests, regresión/cobertura, alcance sensible) -->
- **slug**: `robustez-panel`
- **fecha**: 2026-10-08
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): robustez-panel`. El hash se anota en `## Registro de verificación`.
- **objetivo**: que el mapa y `me/puntos` dejen de contar las recorridas de los administradores, que una corrección de coordenadas o de "activo" desde el panel o el admin respete las reglas del dominio, y que los filtros, el historial, el CSS y la geocodificación del panel no den 500, no tengan consultas sin tope y no muestren estilos rotos.
- **fuera de alcance**:
  - la concurrencia de dominio (P-robustez-datos-5, -6, -10, -12), que va a `robustez-dominio`;
  - el fixture de contenido y `cargar_demo` (P-sitio-publico-3, -6), que van a `sitio-cierre`;
  - el admin de `apps/web` (P-sitio-publico-12);
  - `config/`, `templates/panel/base.html` y `apps/*/urls.py`.
- **áreas**: panel | api (solo `me/puntos`, que cambia de resultado y no de contrato) | dominio | web
- **seguridad**: sí. El plan toca:
  - geolocalización y atribución a empleados (`ubicacion_fijada_por/en`, T1);
  - el estado que ve el empleado en `me/puntos` (T1);
  - la consulta saliente a Nominatim (T3);
  - la validación de URLs que publica el sitio (T4);
  - las pruebas de permisos del panel (T10);
  - las cabeceras CSP del mapa (`csp_update` de `MapaDatosView`, T10);
  - el admin de sitios (`PuntoControlAdmin`, con `_AdministradorMixin` y permisos, T1).

  Por eso corren `auditor-seguridad`, `verificador` y `verificador-b`.

## Contexto mínimo

**P-robustez-datos-8** (las coordenadas fijadas no se limpian al corregirlas):
- `PuntoEdicion` (`apps/sitios/panel_views.py:225`) no tiene `form_valid`.
- `PuntoControlAdmin` (`apps/sitios/admin.py:85`) no tiene `save_model`.
- Ninguno de los dos limpia `ubicacion_fijada_por/en`. En cambio, `services.fijar_ubicacion*` (`apps/sitios/services.py:86-103`, `:221-246`) sí los limpia.

**P-robustez-datos-9** (las recorridas de los administradores cuentan):
- `estado_revision` (`apps/sitios/estado.py:53-57`) y `estados_de_puntos` (`:78-84`) filtran solo por estado.
- `apps/panel/mapa.py:33-37` ya usa `cuenta_como_servicio=True`.
- `estados_de_puntos` lo consumen el mapa, `panel/estado.py`, la ficha del sitio, el plano de la API y `MisPuntosView`.

**P-robustez-datos-1** (se puede desactivar el último punto activo):
- `PuntoForm` (`apps/sitios/panel_forms.py:32`, campo `activo` en `:41`) expone `activo` sin pasar por `desactivar_punto` (`services.py:127-142`, que bloquea y rechaza el último punto activo).
- El admin tiene el mismo hueco.
- El checkbox es la única forma de reactivar un punto, así que no se quita.

**Resto del panel:**
- `isdigit()` sin `isascii()` en `apps/panel/views.py:63`, `apps/sitios/panel_views.py:51`, `apps/proyectos/panel_views.py:52` y `apps/visitas/panel_views.py:73`.
- `_historial` (`apps/visitas/panel_views.py:102-121`) hace `prev_record` por fila.
- Las incidencias se cuentan distinto en `apps/visitas/panel_views.py:81-84` y en `apps/panel/tablero.py:29-43`.
- Hay clases sin estilo: `.enlace`, `.linea-tiempo`, `.miniaturas`, `.planilla` y `.fotos`.
- `tablero.html` y `mapa.html` tienen un `<style nonce>` propio.
- `csp_update` sobra en `apps/panel/views.py:45`.
- En `apps/sitios/geocodificacion.py`, `RecursionError` no se captura en `:109-110`, el User-Agent de `:20` no da contacto y el timeout de `:21` es por socket.

**Sitio público:**
- `clean_redes` (`apps/web/forms.py:82-92`) acepta URLs con `usuario:contraseña@`.
- `404.html` (`apps/web/templates/`) enlaza a `/` también desde `/panel/` y `/admin/`.

Ninguna subtarea crea migraciones: los campos `ubicacion_fijada_*` y `cuenta_como_servicio` ya existen.

## Olas

Se pidió poner primero los importantes y después ordenar por app según el grafo de FK. `sitios` y `web` comparten nivel porque `web` solo depende de `servicios`. `panel` es transversal y va última.

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1, T2 (integración) | sitios (ninguna) — importantes -8, -9, -1 |
| 2 | T3, T4, T5 (integración) | sitios, web (ninguna) |
| 3 | T6, T12, T7 (integración) | proyectos, sitios (ninguna) — T12 agregada por contrato modificado (T3-3) |
| 4 | T8, T9 (integración) | visitas (ninguna) |
| 5 | T10, T11 (integración y cierre) | panel transversal y diseño (ninguna) |

## Subtareas

En todas las subtareas, salvo que se indique otra cosa:
- **No puede tocar**: `docs/planes/`, `config/`, `apps/*/urls.py`, `apps/*/migrations/` y cualquier app que no sea la suya.
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md`.
- **Worktree**: sí (`worktrees/robustez-panel-T<n>`, base `plan/robustez-panel`).
- **Ruta**: delegada (`implementador`).
- **Presupuesto**: 400 líneas agregadas.

Toda subtarea que corrige un defecto lleva al menos un `[test]` que lo reproduce y que falla antes del cambio. Las subtareas que solo agregan cobertura (P-panel-27 en T8, AccesoTests en T10) llevan `[test]` nuevos y nombrados, sin ese requisito; se declaran como cobertura en su bloque Criterios.

### T1 — Coordenadas, estado y "activo" de los puntos (P-robustez-datos-8, -9, -1)

- **Ola**: 1 · **Depende de**: —
- **Puede tocar**: `apps/sitios/estado.py`, `apps/sitios/panel_views.py`, `apps/sitios/panel_forms.py`, `apps/sitios/admin.py`, `apps/sitios/tests/test_models.py`, `apps/sitios/tests/test_panel.py`, `apps/sitios/tests/test_admin.py`
- **Qué hacer**:
  - **-9**: agregar `visita__cuenta_como_servicio=True` a los dos filtros de `estado.py`.
  - **-8**: si `latitud` o `longitud` están en `changed_data`, `PuntoEdicion.form_valid` y `PuntoControlAdmin.save_model` ponen en `None` `ubicacion_fijada_por` y `ubicacion_fijada_en`.
  - **-1**: si `activo` pasa de `True` a `False`, la edición del panel y la del admin desactivan con `services.desactivar_punto`. Si el servicio lo rechaza, el error se muestra en el formulario (`add_error("activo", …)`) y no se guarda nada. Reactivar sigue funcionando con el checkbox.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_models.EstadoRevisionTests.test_estado_revision_ignora_visitas_de_administrador --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_models.EstadoRevisionTests.test_estados_de_puntos_ignora_visitas_de_administrador --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel.PuntoPanelTests.test_corregir_coordenadas_limpia_fijada_por_escaneo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel.PuntoPanelTests.test_editar_sin_cambiar_coordenadas_conserva_fijada --keepdb` — (regresión)
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_admin.PuntoControlAdminTests.test_corregir_coordenadas_limpia_fijada_por_escaneo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel.PuntoPanelTests.test_destildar_activo_del_ultimo_punto_se_rechaza --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel.PuntoPanelTests.test_destildar_activo_con_otro_activo_desactiva --keepdb` — (regresión)
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_admin.PuntoControlAdminTests.test_no_desactiva_el_ultimo_punto --keepdb`
  - `[cmd]` `test "$(grep -c 'visita__cuenta_como_servicio=True' apps/sitios/estado.py)" -ge 2`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios apps.panel --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T1`

### T2 — Integración ola 1 (principal)

- **Ola**: 1 · **Depende de**: T1
- **Pasos**:
  1. Revisar `cambios.sh`.
  2. `worktree-integrar.sh robustez-panel T1 plan/robustez-panel apps/sitios`.
  3. `verificador`, `verificador-b` y `auditor-seguridad` sobre T1.
  4. Presentar las decisiones de la ola.
  5. Crear T3 y T4.
- **Presupuesto**: no aplica.
- **Criterios**:
  - `[cmd]` `git log --oneline plan/robustez-panel | grep -q "T1: integra robustez-panel-T1"`

### T3 — Filtro y geocodificación de sitios (P-panel-10 en sitios, P-panel-18, P-panel-20)

- **Ola**: 2 · **Depende de**: T2
- **Puede tocar**: `apps/sitios/panel_views.py`, `apps/sitios/geocodificacion.py`, `apps/sitios/tests/test_panel.py`, `apps/sitios/tests/test_geocodificacion.py`
- **Qué hacer**:
  - El filtro `cliente` usa `isascii() and isdigit()`.
  - `RecursionError` entra en la tupla del `except`, y la respuesta es 503 con el mensaje de carga manual.
  - El User-Agent pasa a ser `MAControl/1.0 (+<settings.SITE_URL>; administracion@macontrol.com.ar)`. El correo es el de `docs/00-contenido-fuente.md:9`.
  - La consulta tiene una fecha límite total de 5 s con `time.monotonic()`, leyendo en bloques. Si se pasa del tiempo, también responde 503.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel.SitioPanelTests.test_filtro_cliente_no_ascii_no_da_500 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_geocodificacion.GeocodificacionTests.test_json_muy_anidado_responde_503 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_geocodificacion.GeocodificacionTests.test_user_agent_lleva_contacto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_geocodificacion.GeocodificacionTests.test_respuesta_lenta_corta_por_tiempo_total --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T3`

### T4 — Redes y 404 del sitio público (P-sitio-publico-13, -9)

- **Ola**: 2 · **Depende de**: T2
- **Puede tocar**: `apps/web/forms.py`, `apps/web/templates/404.html`, `apps/web/tests/test_seguridad_contenido.py`, `apps/web/tests/test_paginas.py`
- **Qué hacer**:
  - `clean_redes` rechaza las URLs que tengan `urlsplit(url).username` o `password`.
  - `404.html` usa `request_path`: bajo `/panel/` enlaza a `/panel/`, bajo `/admin/` a `/admin/` y en el resto a `/`. Sigue sin datos y con `noindex`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_seguridad_contenido.RedesTests.test_redes_rechaza_url_con_usuario_o_contrasena --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_paginas.ErroresTests.test_404_bajo_panel_enlaza_al_panel --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T4`

### T5 — Integración ola 2 (principal)

- **Ola**: 2 · **Depende de**: T3, T4
- **Pasos**: los de T2, con T3 (`apps/sitios`) y T4 (`apps/web`). Al final se crea T6.
- **Presupuesto**: no aplica.
- **Criterios**:
  - `[cmd]` `git log --oneline plan/robustez-panel | grep -q "T3: integra robustez-panel-T3"`
  - `[cmd]` `git log --oneline plan/robustez-panel | grep -q "T4: integra robustez-panel-T4"`

### T6 — Filtro numérico de proyectos (P-panel-10 en proyectos)

- **Ola**: 3 · **Depende de**: T5
- **Puede tocar**: `apps/proyectos/panel_views.py`, `apps/proyectos/tests/test_panel.py`
- **Qué hacer**: `isascii() and isdigit()` en el filtro de `:52`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.proyectos.tests.test_panel.ProyectoPanelTests.test_filtro_numerico_no_ascii_no_da_500 --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.proyectos --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T6`

### T12 — Cota total de tiempo en la geocodificación (T3-3, P-robustez-panel-7)

Agregada por contrato modificado (decisión del usuario, 2026-10-12): el hallazgo T3-3 de auditor-seguridad en la ronda 2 de T3 quedó abierto tras las dos rondas.

- **Ola**: 3 · **Depende de**: T5
- **Puede tocar**: `apps/sitios/geocodificacion.py`, `apps/sitios/tests/test_geocodificacion.py`
- **Qué hacer**:
  - La consulta a Nominatim usa `http.client.HTTPSConnection` (sin seguir redirecciones; todo estado distinto de 200 responde 503) y un vigilante (`threading.Timer`) que corta el socket al vencer `LIMITE_TOTAL_SEGUNDOS`. Así la cota total de 5 s cubre las cabeceras, las líneas de control del chunked (tamaño de trozo, trailer) y el cuerpo.
  - Se mantienen el User-Agent con contacto, el tope de 1 MB, la lectura con `read1` y las excepciones que hoy responden 503. El docstring de `_abrir` describe el límite real, incluida la resolución DNS si queda fuera de la cota.
  - Los tests de T3 que son criterios conservan su nombre y siguen en verde; se puede adaptar su mock a la nueva forma de abrir la conexión.
- **Presupuesto**: 300 líneas agregadas.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_geocodificacion.GeocodificacionTests.test_cabeceras_goteadas_cortan_por_tiempo_total --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_geocodificacion.GeocodificacionTests.test_linea_de_trozo_goteada_corta_por_tiempo_total --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_geocodificacion.GeocodificacionTests.test_redireccion_responde_503 --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 --subtarea T12`

### T7 — Integración ola 3 (principal)

- **Ola**: 3 · **Depende de**: T6, T12
- **Pasos**: los de T2, con T6 (`apps/proyectos`) y T12 (`apps/sitios`). Al final se crea T8.
- **Presupuesto**: no aplica.
- **Criterios**:
  - `[cmd]` `git log --oneline plan/robustez-panel | grep -q "T6: integra robustez-panel-T6"`
  - `[cmd]` `git log --oneline plan/robustez-panel | grep -q "T12: integra robustez-panel-T12"`

### T8 — Incidencias, historial y ficha de visitas (P-robustez-datos-3, P-panel-21, P-robustez-datos-11 listado, P-panel-10, -22, -27)

- **Ola**: 4 · **Depende de**: T7
- **Puede tocar**: `apps/visitas/panel_views.py`, `apps/visitas/panel_forms.py`, `apps/visitas/templates/visitas/panel/**`, `apps/visitas/tests/test_panel.py`, `apps/visitas/tests/test_admin.py`
- **Qué hacer**, en orden menor → observación:
  - **-3**: el filtro `incidencia` suma la opción `ubicacion_revisadas` (incidencias de ubicación ya revisadas). La opción `ubicacion` no cambia.
  - **P-panel-21**: `_historial` trae los últimos 50 registros en una sola consulta (`select_related("history_user")`), compara cada uno con el siguiente de la lista y no usa `prev_record`.
  - **-11**: el listado `ubicacion` filtra `cuenta_como_servicio=True` y `estado=REALIZADA`, igual que el tablero de T10.
  - **P-panel-10**: `isascii()` en `:73`.
  - **P-panel-22**: la ficha muestra `incidencia_asignacion`.
  - **P-panel-27**: un test nuevo comprueba el código de respuesta y el mensaje del rechazo de un POST forjado sobre una pendiente. El mensaje actual de `Visita.clean` es "Una visita pendiente no tiene revisiones.".
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel.ListadoVisitasTests.test_filtro_ubicacion_revisadas_lista_solo_revisadas --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel.FichaVisitaTests.test_historial_con_consultas_acotadas --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel.ListadoVisitasTests.test_filtro_ubicacion_excluye_administradores_y_abiertas --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel.ListadoVisitasTests.test_filtro_numerico_no_ascii_no_da_500 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel.FichaVisitaTests.test_muestra_incidencia_de_asignacion --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_admin.AdminPendienteTests.test_post_forjado_sobre_pendiente_muestra_el_rechazo --keepdb` — (cobertura)
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T8`

### T9 — Integración ola 4 (principal)

- **Ola**: 4 · **Depende de**: T8
- **Pasos**: los de T2, con T8 (`apps/visitas`). Al final se crea T10.
- **Presupuesto**: no aplica.
- **Criterios**:
  - `[cmd]` `git log --oneline plan/robustez-panel | grep -q "T8: integra robustez-panel-T8"`

### T10 — Panel transversal y diseño (P-cierre-puntos-1, P-robustez-datos-11 tablero, P-panel-9, -10, -12, -19)

- **Ola**: 5 · **Depende de**: T9
- **Puede tocar**: `apps/panel/**` (salvo `apps/panel/urls.py`) y `static/css/panel.css`. T10 es a la vez la subtarea "transversal" y la de "diseño" de este plan.
- **No puede tocar**: `templates/panel/base.html`, `apps/panel/urls.py` y las plantillas de las otras apps.
- **Qué hacer**, en orden menor → observación:
  - **CP-1**: `.enlace` en `panel.css`, con aspecto de enlace.
  - **-11**: los dos contadores de `tablero.py` cuentan solo visitas `REALIZADA`.
  - **P-panel-9**: el CSS de `tablero.html` y `mapa.html` pasa a `panel.css` y se quitan sus `<style nonce>`. También se agregan `.linea-tiempo`, `.miniaturas`, `.planilla` y `.fotos`.
  - **P-panel-10**: `_entero` usa `isascii()`.
  - **P-panel-12**: se quita `csp_update` de `MapaDatosView` y se ajusta `test_mapa_permite_teselas_osm_en_csp`.
  - **P-panel-19**: `AccesoTests` crea objetos reales y prueba el POST anónimo.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_diseno.DisenoTests.test_panel_css_define_enlace --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_tablero.TableroTests.test_incidencias_no_cuentan_visitas_abiertas --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_diseno.DisenoTests.test_tablero_y_mapa_sin_style_propio --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_diseno.DisenoTests.test_clases_de_fichas_tienen_estilo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_mapa.MapaTests.test_filtro_numerico_no_ascii_no_da_500 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_mapa.MapaTests.test_datos_del_mapa_sin_csp_de_teselas --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_acceso.AccesoTests.test_empleado_no_ve_rutas_con_objetos_reales --keepdb` — (cobertura)
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_acceso.AccesoTests.test_anonimo_post_va_al_login --keepdb` — (cobertura)
  - `[grep-0]` `grep -n "<style" apps/panel/templates/panel/tablero.html apps/panel/templates/panel/mapa.html`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T10`

### T11 — Integración ola 5 y cierre (principal)

- **Ola**: 5 · **Depende de**: T10
- **Pasos**:
  1. Integrar T10 (`apps/panel`, `static/css/panel.css`).
  2. Agregar a `### Cierra` los pendientes resueltos.
  3. Correr `verificador`, `verificador-b` y `auditor-seguridad` sobre `TODO`.
  4. El merge a `main` lo decide el usuario.
- **Presupuesto**: no aplica.
- **Criterios**:
  - `[cmd]` `git log --oneline plan/robustez-panel | grep -q "T10: integra robustez-panel-T10"`

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-08-robustez-panel.md robustez-panel`

## Registro de verificación

commit_base: 21b20be

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | hecha |
| T2 | hecha |
| T3 | hecha |
| T4 | hecha |
| T5 | hecha |
| T6 | hecha |
| T7 | hecha |
| T8 | pendiente |
| T9 | pendiente |
| T10 | pendiente |
| T11 | pendiente |
| T12 | hecha |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| 2026-10-08 | T1 (ronda 1) | 5beddf5 | verificador PASA 11/11; verificador-b PASA 11/11 | auditor-seguridad: 1 importante (alta en admin rechazada, regresión de T1), 2 menores, 2 observaciones; el usuario decide corregir en T1 antes de integrar |
| 2026-10-08 | T1 (ronda 2) | c516ab7 | verificador PASA 11/11; verificador-b PASA 11/11 | auditor-seguridad: hallazgos 1-3 y la observación de precision_m cerrados; queda 1 Baja ya existente antes de T1 (P-robustez-panel-2) y el historial doble (P-robustez-panel-1) |
| 2026-10-08 | T2 | a5c66bc | criterio `T1: integra robustez-panel-T1` PASA (principal) | worktree-integrar.sh: merge, makemigrations --check y 624 tests OK; falló solo el `git branch -d` final (P-robustez-panel-3); rama borrada a mano tras comprobar que estaba contenida |
| 2026-10-12 | T3 (ronda 1) | 3ee6a27 | verificador PASA 6/6; verificador-b PASA 6/6 | auditor-seguridad: T3-1 [Baja] la fecha límite total no corta lecturas goteadas; T3-2 [Baja] OverflowError y HTTPException escapan (anterior a T3); se corrigen en T3 ronda 2 |
| 2026-10-12 | T4 | 3608ef0 | verificador PASA 4/4; verificador-b PASA 4/4 | auditor-seguridad: sin hallazgos; nota latente: el admin de `Configuracion` no pasa por `clean_redes` (P-robustez-panel-5). Integrada en e5d01d0 (626 tests OK); otra vez falló solo el `branch -d` (P-robustez-panel-3) |
| 2026-10-12 | T3 (ronda 2) | 613d341 | verificador PASA 6/6; verificador-b PASA 6/6 | auditor-seguridad: T3-1 cerrado para el cuerpo, T3-2 cerrado; nuevo T3-3 [Baja] (líneas de control del chunked y cabeceras goteadas sin cota total, docstring inexacto) queda abierto como P-robustez-panel-7; test con socket real estable 3/3 |
| 2026-10-12 | T5 | 87e96af | criterios `T3: integra` y `T4: integra` PASA (principal) | T3 integrada en 87e96af: merge, makemigrations --check y 633 tests OK; otra vez falló solo el `branch -d` (P-robustez-panel-3), rama borrada tras comprobar que estaba contenida |
| 2026-10-12 | T6 | e44f20b | verificador 3/3 PASA, verificador-b 3/3 PASA; veredicto formal FALLA solo por CONTRATO MODIFICADO (fa3397f, T12 por decisión del usuario), bloque de T6 idéntico en 21b20be y fa3397f | auditor-seguridad: sin regresiones; dos Baja anteriores a T6 (P-robustez-panel-8). Integrada en 9060ba3 (634 tests OK); otra vez falló solo el `branch -d` (P-robustez-panel-3) |
| 2026-10-12 | T12 (ronda 1) | dca443e | verificador 5/5 PASA, verificador-b 5/5 PASA (más 4 tests de T3 en PASA); veredicto formal FALLA solo por CONTRATO MODIFICADO (fa3397f) | auditor-seguridad: T12-1 [Baja] con `Connection: close` el vigilante no corta la línea de trozo ni el trailer goteados; T12-2 [Baja, PLAUSIBLE] `SSLSocket.shutdown` desde el vigilante puede dar 500 o mandar el pedido en claro (regresión de T12); se corrigen en T12 ronda 2. Sin indicios de proxy de salida |
| 2026-10-12 | T12 (ronda 2) | bf482b5 | verificador 5/5 PASA, verificador-b 5/5 PASA (más 4 tests de T3 en PASA; test_geocodificacion estable 3/3); veredicto formal FALLA solo por CONTRATO MODIFICADO (fa3397f) | auditor-seguridad: T3-3, T12-1 y T12-2 cerrados (9 casos de goteo en HTTP y 8 en TLS cortan a 1 s; intercalado forzado da 503), sin hallazgos nuevos |
| 2026-10-12 | T7 | 82df1a9 | criterios `T6: integra` y `T12: integra` PASA (principal) | T12 integrada en 82df1a9: merge, makemigrations --check y 641 tests OK; otra vez falló solo el `branch -d` (P-robustez-panel-3), rama borrada tras comprobar que estaba contenida |
| | T8 | | | |
| | T9 | | | |
| | T10 | | | |
| | T11 | | | |
| | TODO | | | |

### Veredicto de juez-plan

Pegado sin editar, dentro de un bloque de texto para que sus encabezados no alteren la estructura del plan. Los números de línea que cita son los de la versión juzgada; después se corrigieron las líneas 28 y 36 y se aplicaron los tres ajustes del usuario (2026-10-08), que desplazan la numeración.

```text
# Juicio de plan — robustez-panel

Plan: C:\Users\Emanuel\Desktop\WEB\MaControl\worktrees\robustez-panel\docs\planes\2026-10-08-robustez-panel.md

## (a) Ya existe
- ninguno. Ninguno de los 26 nombres de test nuevos aparece hoy en el repo (lo comprobé con `git grep "def <nombre>"`). El único que ya existe es `test_mapa_permite_teselas_osm_en_csp` (apps/panel/tests/test_mapa.py:205), y el plan lo nombra como test que se ajusta, no como criterio nuevo. `.linea-tiempo`, `.miniaturas`, `.planilla` y `.fotos` no están definidas en ningún CSS. `.enlace` solo existe en static/css/web.css:147, no en panel.css. Ninguna de las vistas toca `form_valid`/`save_model` (el único `form_valid` está en panel_views.py:331, que es otra vista). Tampoco hay un helper de `isascii` que se vaya a duplicar: el único uso está en apps/clientes/validators.py:15, que no es un filtro.

## (b) Criterios
- [observación] docs/planes/2026-10-08-robustez-panel.md:90 — T1 `...test_panel.PuntoPanelTests.test_editar_sin_cambiar_coordenadas_conserva_fijada` — hoy nada limpia `ubicacion_fijada_*`, así que este test pasa antes del cambio. Sirve como guarda de regresión, no como prueba de -8. La prueba real de -8 está en las líneas 89 y 91, así que la subtarea sigue cubierta.
- [observación] docs/planes/2026-10-08-robustez-panel.md:93 — T1 `...PuntoPanelTests.test_destildar_activo_con_otro_activo_desactiva` — hoy el form ya guarda `activo=False` cuando hay otro punto activo, así que el test pasa antes del cambio. -1 sí lo prueban las líneas 92 y 94.
- [observación] docs/planes/2026-10-08-robustez-panel.md:186 — T8 `...test_admin.AdminPendienteTests.test_post_forjado_sobre_pendiente_muestra_el_rechazo` — P-panel-27 es solo de cobertura (no cambia código), así que el test pasa en cuanto se escribe. Lo mismo vale para T10 en las líneas 217-218 (`AccesoTests`, P-panel-19). No es un defecto del contrato: estos pendientes son justamente "agregar un test". Lo anoto porque la línea 76 dice "Cada defecto lleva un [test] nuevo que falla antes del cambio".

Lo que comprobé y está bien:
- **Clases de test:** las 15 existen en los archivos indicados: test_models.py:154, test_panel.py:37/337, sitios/test_admin.py:73, test_geocodificacion.py:19, test_seguridad_contenido.py:126, test_paginas.py:153, proyectos/test_panel.py:27, visitas/test_panel.py:76/153, visitas/test_admin.py:244, panel/test_diseno.py:21, test_tablero.py:18, test_mapa.py:21, test_acceso.py:104. Cada archivo de test figura en el `Puede tocar` de su subtarea.
- **Criterios que hoy fallan como deben:** el `[cmd] grep -c ... -ge 2` de la línea 95 da 0 hoy. El `[grep-0] "<style"` de la línea 219 hoy encuentra tablero.html:5 y mapa.html:9.
- **Integraciones:** los mensajes de las líneas 110/148/149/167/196/233 coinciden con worktree-integrar.sh:151 (`"$tarea: integra $nombre"`). "T1: integra" no coincide por subcadena con "T10: integra".
- **Presupuesto y formato:** `--subtarea T1` no cuenta los commits `T10:` (presupuesto.sh:123). Todos los comandos llevan el prefijo canónico. Los encabezados son `### T<n>` y la tabla de estado está completa. No hay migraciones.

## (c) Mismo archivo
- ninguno.
  - T1 y T3 comparten apps/sitios/panel_views.py y apps/sitios/tests/test_panel.py, pero T3 depende de T1 a través de T2 (líneas 101 y 114).
  - T3 (sitios) y T4 (web) son de la misma ola y sus `Puede tocar` no se cruzan.
  - **Propiedad:** según la tabla de .claude/skills/convenciones-proyecto/SKILL.md:64-73, `apps/panel/**` (sin urls.py) y `static/css/**` son de T10. La línea 201 lo declara transversal y diseño a la vez, y la decisión de la línea 297 lo respalda. Ninguna subtarea de dominio declara archivos de otro dueño.

## (d) Seguridad
- [observación] docs/planes/2026-10-08-robustez-panel.md:14-19 — la lista de alcance sensible no incluye dos cosas que el plan toca:
  - en T10, quitar `csp_update` de `MapaDatosView` (apps/panel/views.py:45), que es un cambio de cabeceras CSP;
  - en T1, el admin de sitios (apps/sitios/admin.py), con `_AdministradorMixin` y permisos.

  No bloquea: el encabezado ya dice `seguridad: sí` y `auditor-seguridad` corre en todas las subtareas (línea 341).

## Contexto mínimo (referencias archivo:línea)
Están bien:
- apps/sitios/panel_views.py:225 (`PuntoEdicion`, sin `form_valid`) y :51 (`isdigit`)
- apps/sitios/admin.py:85 (sin `save_model`)
- apps/sitios/services.py:86-103 y :127-142
- apps/sitios/estado.py:53-57 y :78-84
- apps/panel/mapa.py:33-37
- apps/panel/views.py:45 (es `MapaDatosView`; la de :32 es `MapaView` y se queda) y :63
- apps/proyectos/panel_views.py:52
- apps/visitas/panel_views.py:73, :81-84 y :102-121 (la función termina en :120)
- apps/panel/tablero.py:29-43
- apps/sitios/geocodificacion.py:20, :21 y :109-110
- apps/web/forms.py:82-92
- docs/00-contenido-fuente.md:9 (el correo administracion@macontrol.com.ar)
- `MisPuntosView` está en apps/sitios/api_views.py:206, así que lo cubre `test apps.sitios` en T1.

Tienen errores:
- [observación] docs/planes/2026-10-08-robustez-panel.md:36 — dice `PuntoForm` (`apps/sitios/panel_forms.py:39`), pero la clase está en :32 y el campo `"activo"` en :41. La línea 39 es `"sector"`.
- [observación] docs/planes/2026-10-08-robustez-panel.md:28 — dice `services.py:221-249`, pero `fijar_ubicacion_en_campo` va de :221 a :246. En :245-246 asigna la ubicación al `punto` y con eso termina la función.

## Veredicto
0 bloqueantes, 6 observaciones — APROBADO para congelar.

Todas son observaciones: ninguna es importante ni bloqueante. Las dos referencias de línea de "Contexto mínimo" (líneas 28 y 36) quedan arriba del corte. Si se quieren corregir, tiene que ser antes del commit `docs(plan): robustez-panel`.
```

## Pendientes que deja este plan

### Problemas

- P-robustez-panel-1 [observación] Una baja desde la edición del panel o del admin deja dos filas de historial, ambas con el motivo "Punto desactivado": `desactivar_punto` guarda con `update_fields=["activo"]` (`apps/sitios/services.py:143-145`) y después el formulario hace el guardado completo con `_change_reason` todavía puesto. Se resuelve con un `desactivar_punto` que acepte los campos extra en un solo `save`, o borrando `_change_reason` antes del guardado completo (auditor-seguridad, T1 ronda 2).
- P-robustez-panel-2 [menor] La edición de un punto en el panel o el admin no tiene bloqueo optimista: si un escaneo fija la ubicación entre el GET y el POST, el guardado borra coordenadas y marca de escaneo y el historial lo atribuye al administrador (`apps/sitios/panel_views.py:235-240`, `apps/sitios/admin.py:133-138`, `apps/visitas/services.py:310-325`). Ya existía antes de T1. Corrección propuesta: campo oculto con `ubicacion_fijada_en` o un contador de versión, validado en `clean()`.
- P-robustez-panel-3 [menor] `worktree-integrar.sh` borra la rama de la subtarea con `git -C "$raiz" branch -d`, que compara contra el HEAD de la raíz (`main`) y no contra la rama destino: cuando el destino es `plan/<slug>` en otro worktree, el script sale con exit 1 después de un merge correcto (pasó al integrar T1). Corrección: `git branch -d` desde el worktree destino, o comprobar `merge-base --is-ancestor` contra el destino y usar `-D`.
- P-robustez-panel-4 [observación] La 404 bajo `/panel/` o `/admin/` enlaza a su inicio, pero el botón sigue diciendo "Volver al inicio"; cambiar el texto es decisión de contenido (implementador de T4).
- P-robustez-panel-5 [observación] `ConfiguracionAdmin` (`apps/web/admin.py:6-8`) usa el ModelForm por defecto y no pasa por `clean_redes`: desde `/admin/` se puede guardar cualquier URL en `redes`. Hoy ninguna plantilla pública muestra `redes`; pasa a hallazgo el día que se publique. Corrección: `form = ConfiguracionForm` o un validador en el campo del modelo (auditor-seguridad, T4).
- P-robustez-panel-6 [observación] `test_404_bajo_panel_enlaza_al_panel` arma `404.html` con `render_to_string` y no hace un GET real; hoy no hay `handler404` propio y Django pasa `request_path` (`django/views/defaults.py:59`), así que cubre el caso real (verificador, T4).
- P-robustez-panel-7 [menor] La geocodificación no tiene cota total de tiempo para las cabeceras ni para las líneas de control del chunked (tamaño de trozo, trailer): un servidor que las gotee retiene el worker mucho más de 5 s. El docstring de `_abrir` (`apps/sitios/geocodificacion.py:55-58`) dice que el cuerpo goteado se acota a `LIMITE_TOTAL_SEGUNDOS + TIMEOUT_SEGUNDOS`, lo que no vale para chunked, y la línea 122 del plan declara "fecha límite total de 5 s". Corrección: documentar el límite real o usar `http.client.HTTPSConnection` con un `threading.Timer` que corte el socket al vencer el plazo, con un test que gotee la línea de tamaño de trozo (auditor-seguridad, T3 ronda 2; T3-3).
- P-robustez-panel-8 [menor] Los filtros numéricos del panel convierten con `int(valor)` sin acotar la magnitud: más de 4300 dígitos dan `ValueError` (límite de `sys.int_max_str_digits`) y un id mayor que 2^63-1 da `OverflowError` en SQLite (en Postgres es probable que devuelva vacío). Ambos dan 500, solo para un administrador. Verificado en `apps/proyectos/panel_views.py:52-53`; el mismo patrón está en `apps/sitios/panel_views.py:52`, `apps/panel/views.py:63` y `apps/visitas/panel_views.py:73`. Corrección: `len(valor) <= 19` y `int(valor) <= 2**63 - 1` antes de filtrar, con un test por caso (auditor-seguridad, T6).
### Decisiones

- 2026-10-08 — al corregir coordenadas a mano (panel, admin y `services.fijar_ubicacion`) también se limpia `precision_m`, junto con `ubicacion_fijada_por/en` — la precisión de la fijación anterior no corresponde a la ubicación nueva (observación de auditor-seguridad sobre T1) — decisión del usuario — reemplaza a: (nada)
- 2026-10-08 — la ronda 2 de T1 puede tocar `apps/sitios/services.py` (solo `fijar_ubicacion`), fuera de su `Puede tocar`, sin modificar el contrato congelado — lo exige la decisión anterior sobre `precision_m` — decisión del usuario — reemplaza a: (nada)
- 2026-10-08 — partición por presupuesto siempre en subtarea nueva (T<m>) con presupuesto y criterios propios, declarada como contrato modificado; no se usan sufijos T<n>b — presupuesto.sh --subtarea T<n> suma los T<n>b: y hace fallar el criterio — reemplaza a: 2026-10-04
- 2026-10-08 — P-sitio-publico-3 pasa a `sitio-cierre` y no entra en este plan — depende de que el fixture deje de incluir `TipoServicio` (P-sitio-publico-6) — decisión del usuario — reemplaza a: (nada)
- 2026-10-08 — el filtro de incidencias de visitas suma la opción "ubicación (revisadas)" — P-robustez-datos-3 — decisión del usuario — reemplaza a: (nada)
- 2026-10-08 — que el alta de proyecto copie el encargado inicial al actual es intencional (`docs/01-modelo-y-arquitectura.md:80`, `encargado_actual` obligatorio) — P-panel-14 — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-08 — que el filtro del mapa use `EstadoPunto` mientras el popup usa `EstadoVisita`, y que un sitio nuevo aparezca `sin_revisar` por su punto General, es coherente y lo cubre `test_mapa` — P-puntos-control-26 — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-08 — se aceptan dos llamadas a `esquema_planilla` con una sola consulta, cubiertas por `test_pide_los_campos_del_esquema_una_sola_vez` — P-robustez-datos-4 — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-08 — T10 es a la vez la subtarea transversal y la de diseño, para que el CSS y los tests de `apps/panel` tengan un único dueño — tabla de propiedad — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-08 — `isdigit()` se corrige con `isascii()` en cada app, sin un helper compartido — evita depender de `apps/panel` desde las apps de dominio — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-08 — el listado `?incidencia=ubicacion` y los contadores del tablero cuentan solo visitas realizadas con `cuenta_como_servicio` — solo esas se pueden marcar (decisión 2026-10-08) y los administradores ya se excluyen del contador (2026-10-07) — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-08 — el historial de la ficha de visita muestra los últimos 50 cambios — P-panel-21 — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-08 — el User-Agent de Nominatim lleva `SITE_URL` y administracion@macontrol.com.ar, y la consulta tiene un tope total de 5 s — P-panel-20, política de Nominatim — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-08 — la 404 bajo `/panel/` o `/admin/` enlaza a su propio inicio, sin handler en `config/` — P-sitio-publico-9 — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-08 — la desactivación desde el admin también pasa por `desactivar_punto` — mismo hueco que P-robustez-datos-1 — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-08 — el worktree del plan se crea con `git worktree add` y una junction — `worktree-crear.sh` solo crea `<slug>-T<n>` — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-08 — etiquetas nuevas `robustez-dominio` (concurrencia y archivos del dominio), `robustez-api` y `rendimiento-web` — ningún destino existente encaja — reemplaza a: (nada) — decidida por Claude, revisable

- 2026-10-08 — -8 en el panel y el admin limpia `ubicacion_fijada_por/en` y `precision_m` en el formulario, sin llamar a `services.fijar_ubicacion` — el formulario guarda los demás campos en un solo `save` — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-08 — la regla del último punto activo en el admin se valida en `PuntoControlAdminForm.clean()` (solo en edición, con `select_for_update`) y `save_model` llama a `services.desactivar_punto` — el error aparece en el formulario y el servicio sigue siendo la regla que decide — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-08 — en el panel, `desactivar_punto(form.instance)` corre antes del guardado completo del formulario, dentro del mismo `atomic` — toma los bloqueos antes de escribir y evita el deadlock de la ronda 1 — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-12 — los hallazgos T3-1 (fecha límite que no corta lecturas goteadas) y T3-2 (OverflowError y HTTPException que dan 500) se corrigen en T3 antes de integrar — T3-1 es un control que T3 declara y no cumple, mismo criterio que el usuario aplicó a T1; T3-2 es el mismo `except` y el mismo objetivo (503 en vez de 500) — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-12 — T3-3 (P-robustez-panel-7) se resuelve en una subtarea nueva, T12, en la ola 3 junto a T6, con su integración en T7; contrato modificado en fa3397f, así que `congelado.sh` sale con 1 (CONTRATO MODIFICADO) hasta el cierre — el hallazgo quedó abierto tras las dos rondas de T3 — decisión del usuario — reemplaza a: (nada)
- 2026-10-12 — los hallazgos T12-1 (`Connection: close` sin corte) y T12-2 (carrera con `SSLSocket.shutdown`) se corrigen en T12 antes de integrar — T12-1 es una variante del objetivo de T12 y T12-2 una regresión introducida por T12, mismo criterio que el usuario aplicó a T1 — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-12 — la geocodificación deja de respetar `HTTPS_PROXY`/`no_proxy` del entorno al pasar a `HTTPSConnection` — no hay proxy de salida en el repo (auditor-seguridad, T12); si el hosting lo exige, falla visible con 503 y se repone con `set_tunnel` — reemplaza a: (nada) — decidida por Claude, revisable

### Cierra

- cierra: P-sitio-publico-17 — resuelto por los ajustes visuales del usuario, commit 80f8ed7 en main
- cierra: P-panel-14 — comportamiento intencional (ver Decisiones)
- cierra: P-puntos-control-26 — comportamiento coherente y cubierto por `test_mapa` (ver Decisiones)
- cierra: P-robustez-datos-4 — se acepta la resolución con prefetch (ver Decisiones)

<!-- Los pendientes que resuelven T1–T10 se agregan acá en T11, al verlos en PASA. -->

### Etiquetas

- etiqueta: P-robustez-datos-1 → robustez-panel — importante, ola 1
- etiqueta: P-robustez-datos-2 → robustez-api
- etiqueta: P-robustez-datos-3 → robustez-panel
- etiqueta: P-robustez-datos-4 → robustez-panel — se resuelve como decisión
- etiqueta: P-robustez-datos-5 → robustez-dominio
- etiqueta: P-robustez-datos-6 → robustez-dominio
- etiqueta: P-robustez-datos-7 → despliegue — "antes del despliegue"
- etiqueta: P-robustez-datos-10 → robustez-dominio
- etiqueta: P-robustez-datos-11 → robustez-panel
- etiqueta: P-robustez-datos-12 → robustez-dominio
- etiqueta: P-sitio-publico-3 → sitio-cierre — su texto decía robustez-panel; depende de -6 (decisión del usuario)
- etiqueta: P-sitio-publico-5 → sitio-cierre — "se actualiza al fusionar"
- etiqueta: P-sitio-publico-8 → robustez-dominio — su texto dice robustez-datos, un plan ya fusionado
- etiqueta: P-sitio-publico-9 → robustez-panel
- etiqueta: P-sitio-publico-10 → empresa
- etiqueta: P-sitio-publico-11 → empresa
- etiqueta: P-sitio-publico-13 → robustez-panel
- etiqueta: P-sitio-publico-14 → despliegue
- etiqueta: P-sitio-publico-15 → rendimiento-web — "sin destino"
- etiqueta: P-sitio-publico-16 → despliegue — lo resuelve el servido de producción

## Verificación

- **Por subtarea**: `verificador` y `verificador-b` con `<plan> T<n>`. Como el plan lleva `seguridad: sí`, también `auditor-seguridad`. Si los dos verificadores discrepan, decide `refutador`.
- **Al final**: los mismos tres con `TODO`.
- **Etiquetas**: `py -3 .claude/hooks/pendientes.py --json` no tiene que dar avisos, y `--etiqueta robustez-panel` tiene que salir vacío al cierre.
