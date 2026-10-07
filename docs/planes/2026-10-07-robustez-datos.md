# Plan: robustez de datos (servicios, admin, migraciones, archivos y bloqueos)

- **slug**: `robustez-datos`
- **fecha**: 2026-10-07
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): robustez-datos`. El hash se anota en `## Registro de verificación`.
- **objetivo**: cerrar los 28 pendientes con la etiqueta `robustez-datos` más P-cierre-puntos-2: las incidencias de ubicación se pueden atender, los bloqueos tienen un orden único, los archivos reemplazados no quedan huérfanos y las altas de campo no rompen con pedidos grandes.
- **fuera de alcance**: `robustez-panel` (vistas y CSS, salvo P-cierre-puntos-2), despliegue, `expo`, informes, cualquier otro pendiente sin la etiqueta. El contrato de `/api/v1/` no cambia, salvo campos nuevos de solo lectura. Ningún campo nuevo se expone en la API en este plan.
- **áreas**: dominio (modelos y servicios) · panel · api · infraestructura
- **seguridad**: sí. Toca bloqueos y concurrencia de visitas, la geolocalización (`ubicacion_fijada_por/en`, `precision_m`), archivos (borrado de fotos y planos, límite de pedido en `AltaPuntoView`), el enmascarado de datos personales en logs, roles (pendiente no asignable a un administrador, rol al abrir) y el throttle. Corre `auditor-seguridad`.

## Contexto mínimo

- **Bloqueos**: `abrir_visita` bloquea Proyecto → Visita (`apps/visitas/services.py:251-253`) y `cerrar_visita` hace lo inverso (`:514-520`). `marcar_incidencia_revisada` (`:727-742`) no bloquea y rechaza las incidencias de ubicación. `registrar_revision` bloquea la visita antes de mirar el dueño (`:437-444`).
- **Rol del usuario**: se lee al cerrar (`:586`, `:589`), no al abrir. El tablero (`apps/panel/tablero.py:33-42`) y el mapa (`apps/panel/mapa.py:31-35`) cuentan las visitas de administradores.
- **Archivos huérfanos**: `Plano.save` y `PuntoControl.save` (`apps/sitios/models.py:135-153`, `:225-240`) no borran el archivo anterior. El patrón a copiar es `Foto.save` (`apps/visitas/models.py:209-235`). `suprimir_sitio` ya borra los planos por `post_delete`.
- **Pedidos grandes**: `AltaPuntoView` (`apps/sitios/api_views.py:292-324`) lee `request.data` sin cortar antes. El patrón a copiar es `CrearRevisionView.post` (`apps/visitas/api_views.py:166-176`).
- **Throttle**: las altas de sitio, punto y ubicación comparten el cupo `crear_visita` (`config/settings/base.py:213-217`).
- **Transacciones**: `.agents/skills/django-patterns/SKILL.md` no tiene una sección de transacciones ni de bloqueos. La regla de este plan sale del código y de `docs/decisiones.md` (2026-10-03).

## Decisiones del usuario al planificar

- Al reactivar un sitio se reactivan solo los puntos que apagó el sitio: los que tienen como última fila histórica "Sitio desactivado". No hace falta migración.
- El rol se guarda al abrir en `Visita.cuenta_como_servicio`. `visitas.0009` llena las visitas existentes con el rol actual de su empleado.
- Se reestructuran las olas pedidas. T1 lo hace el principal, en línea. La ola 1 tiene A (visitas) y B (sitios). La ola 2 tiene C (`apps/panel` completo, que es la subtarea transversal del panel) y una subtarea chica de visitas que depende del campo de B.

## Contrato entre subtareas (fijo)

- `Visita.cuenta_como_servicio`: `BooleanField(default=True)`. `abrir_visita` lo pone en `False` si `empleado.es_administrador`. Lo crea T2 y lo consume T5.
- `Visita.precision_m`: `DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)`, excluido del historial como en `Revision`. Lo crea T2.
- `Sitio.precision_m` y `PuntoControl.precision_m`: mismo tipo. Los crea T3.
- `PuntoControl.ubicacion_fijada_por`: FK a User, `null=True`, `on_delete=SET_NULL`, `related_name="+"`.
- `PuntoControl.ubicacion_fijada_en`: `DateTimeField(null=True, blank=True)`.
  - Los dos los crea T3 en `sitios.0008`, con backfill desde el historial con motivo "Ubicación fijada por el primer escaneo".
  - Los llena T6 en `_fijar_ubicacion_por_escaneo`.
- Throttle: el cupo nuevo `alta_campo` (`300/hour`) lo define T1 y lo usa T3 en `AltaSitioView`, `AltaPuntoView` y `UbicacionPuntoView`. Las vistas de visitas siguen con `crear_visita`.
- Orden de bloqueo único: **Proyecto → Visita → PuntoControl**. `cerrar_visita` lee el `proyecto_id` sin bloquear, bloquea el Proyecto, después la Visita, y vuelve a comprobar el estado.

## Olas

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1 (principal, en línea, antes de los worktrees), T2, T3, T4 (integración) | visitas `0009`, sitios `0008` |
| 2 | T5, T6, T7 (integración y cierre) | ninguna |

## Subtareas

### T1 — Configuración transversal: cupo alta_campo, cota de pypdfium2, .env.example y enmascarado de "Failing row contains"

- **Ola**: 1 · **Depende de**: —
- **Worktree**: no. Son archivos del principal y van en un commit `T1:` en `plan/robustez-datos`, antes de crear los worktrees. **Ruta**: inline.
- **Puede tocar**: `config/settings/base.py`, `requirements.txt`, `.env.example`, `config/registro.py`, `config/tests/test_registro.py`, `config/tests/test_settings.py`
- **No puede tocar**: `docs/planes/`, `apps/**`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § Variables de entorno
- **Presupuesto**: 120 líneas agregadas
- **Qué hacer**:
  - Agregar `"alta_campo": "300/hour"` a `DEFAULT_THROTTLE_RATES`.
  - Cambiar `pypdfium2` por `pypdfium2>=5.14,<6`.
  - Documentar `DISTANCIA_MAXIMA_M` en `.env.example`, con el rango 50–5000 y el default 300.
  - En `config/registro.py`, agregar una segunda sustitución MULTILINE `Failing row contains \(.*?\)\.?$` → `[oculto]`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_registro.RegistroTests.test_enmascara_failing_row_contains --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_settings.SettingsTests.test_cupo_alta_campo_definido --keepdb`
  - `[grep-1]` `grep -n "DISTANCIA_MAXIMA_M" .env.example`
  - `[grep-1]` `grep -n "pypdfium2[<>=]" requirements.txt`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 120 --subtarea T1`

### T2 — A · Visitas: incidencias de ubicación, orden de bloqueo, rol al abrir, carga manual y admin

- **Ola**: 1 · **Depende de**: T1
- **Worktree**: sí (`worktrees/robustez-datos-T2`)
- **Puede tocar**: `apps/visitas/services.py`, `apps/visitas/models.py`, `apps/visitas/admin.py`, `apps/visitas/panel_views.py`, `apps/visitas/panel_forms.py`, `apps/visitas/api_views.py`, `apps/visitas/management/commands/cerrar_visitas_abiertas.py`, `apps/visitas/management/commands/registrar_revision_demo.py`, `apps/visitas/migrations/0009_*.py`, `apps/visitas/templates/visitas/panel/**`, `apps/visitas/tests/**`
- **No puede tocar**: `docs/planes/`, `config/`, `requirements.txt`, `apps/sitios/**`, `apps/panel/**`, migraciones existentes, `_fijar_ubicacion_por_escaneo` (es de T6)
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § Panel y § Prohibiciones; `.agents/skills/django-patterns/SKILL.md` § Service Layer Pattern
- **Presupuesto**: 700 líneas agregadas
- **Qué hacer**:
  - **P-cierre-puntos-13**:
    - `marcar_incidencia_revisada` acepta `incidencia` o una incidencia de ubicación (en la visita o en alguna revisión).
    - El listado suma el filtro `ubicacion`.
    - La ficha muestra la distancia de la visita y la de cada revisión, y el botón "Marcar como revisada" cuando hay una incidencia de ubicación sin revisar.
  - **P-panel-15**: `atomic` + `select_for_update` dentro del servicio.
  - **P-puntos-control-9**: aplicar el orden del contrato. `cerrar_visitas_abiertas` captura `OperationalError` por visita, lo registra y sigue.
  - **P-cierre-puntos-9**: `.get(pk=…, empleado=empleado)` dentro del `select_for_update`.
  - **P-cierre-puntos-10**: crear `cuenta_como_servicio` y que `cerrar_visita` lo use en lugar del rol actual. `0009` llena las visitas existentes con el rol actual del empleado.
  - **P-cierre-puntos-4 (parte de visitas)**: `abrir_visita` guarda `precision_m`.
  - **P-panel-24**: la carga manual rechaza `realizada_en < proyecto.creado`.
  - **P-panel-25**: la carga manual y `AsignarVisita` rechazan un sitio o un cliente de baja.
  - **P-panel-26**: `_change_reason = "Reasignada en carga manual por <usuario>"`.
  - **P-cierre-puntos-7**: `Visita.clean()` rechaza una pendiente asignada a un administrador, y `VisitaAdmin` limita el campo `empleado`.
  - **P-cierre-puntos-12**: `--proyecto` en `registrar_revision_demo`.
  - **P-panel-7**: `prefetch_related("tipo_servicio__campos")` en `_cargar_proyecto` y `cerrar_visita`, y una sola llamada a `esquema_planilla` en `panel_forms.py`.
  - **Contrato del 409 de revisiones**: un duplicado ajeno no expone `revision` ni `visita`; queda cubierto con un test.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_incidencias.UbicacionTests.test_se_puede_marcar_revisada_y_filtrar --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_incidencias.UbicacionTests.test_ficha_muestra_distancia_y_boton --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_incidencias.UbicacionTests.test_marcar_revisada_bloquea_la_fila --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel.ManualTests.test_rechaza_fecha_anterior_al_proyecto_y_sitio_de_baja --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel.ManualTests.test_reasignar_deja_motivo_en_historial --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel.AsignarTests.test_rechaza_sitio_o_cliente_de_baja --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.BloqueosTests.test_orden_de_bloqueo_proyecto_visita --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.BloqueosTests.test_revision_filtra_por_empleado_al_bloquear --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.BloqueosTests.test_rol_se_evalua_al_abrir --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.PrecisionTests.test_abrir_guarda_precision_m --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.EsquemaTests.test_cargar_proyecto_prefetchea_campos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_comandos.CerrarAbiertasTests.test_operational_error_no_corta_la_corrida --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_comandos.RevisionDemoTests.test_opcion_proyecto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api.RevisionesTests.test_409_no_expone_visita_ajena --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_admin.AdminPendienteTests.test_pendiente_no_asignable_a_administrador --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_migraciones.CuentaComoServicioTests.test_backfill_por_rol --keepdb`
  - `[grep-1]` `grep -n "cuenta_como_servicio = models.BooleanField" apps/visitas/models.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 700 --subtarea T2`

### T3 — B · Sitios: archivos, admin, altas de campo, precisión y ubicación fijada

- **Ola**: 1 · **Depende de**: T1
- **Worktree**: sí (`worktrees/robustez-datos-T3`)
- **Puede tocar**: `apps/sitios/models.py`, `apps/sitios/services.py`, `apps/sitios/admin.py`, `apps/sitios/api_views.py`, `apps/sitios/serializers.py`, `apps/sitios/panel_views.py`, `apps/sitios/planos.py`, `apps/sitios/rasterizar_pdf.py`, `apps/sitios/migrations/0008_*.py`, `apps/sitios/templates/sitios/panel/**`, `apps/sitios/tests/**`
- **No puede tocar**: `docs/planes/`, `config/`, `requirements.txt`, `apps/visitas/**`, `apps/panel/**`, migraciones existentes (`0007` incluida: solo se le agrega un test)
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § Panel y § Prohibiciones
- **Presupuesto**: 650 líneas agregadas
- **Qué hacer**:
  - **P-puntos-control-7, P-cierre-puntos-6**: `Plano.save` y `PuntoControl.save` borran el archivo anterior con `on_commit`, con el patrón de `Foto.save`.
  - **P-puntos-control-8, P-cierre-puntos-6**: `get_readonly_fields` deja de solo lectura `sitio` (en `PuntoControl` y `Plano`) y `foto` al editar.
  - **P-puntos-control-24**: `max_value=2**31 - 1`.
  - **P-puntos-control-27**:
    - `desactivar_punto` rechaza el último punto activo.
    - `Sitio.save`, al reactivar el sitio, reactiva los puntos cuya última fila histórica es "Sitio desactivado", con el motivo "Sitio reactivado".
  - **P-cierre-puntos-4 (parte de sitios)**: `precision_m` en `Sitio` y `PuntoControl`, que guardan las altas de campo y `fijar_ubicacion_en_campo`.
  - **P-cierre-puntos-5**: `AltaPuntoView` corta por `CONTENT_LENGTH` y captura `RequestDataTooBig`, `TooManyFieldsSent` y `TooManyFilesSent`. Responde 400 con el cuerpo de error habitual: el 400 ya es el contrato actual para una foto inválida.
  - **P-cierre-puntos-8**: `fijar_ubicacion*` dentro de `atomic` + `select_for_update`.
  - **P-cierre-puntos-11**: `throttle_scope = "alta_campo"` en las tres vistas de campo.
  - **P-auditoria-p31-1**:
    - Crear los campos `ubicacion_fijada_por/en`, con el backfill en `0008`.
    - Aviso "Punto fijado por escaneo" en `_pestana_puntos.html` y `punto_formulario.html` cuando `ubicacion_fijada_en` tiene valor. No hay ficha propia del punto.
  - **P-auditoria-p31-2**: test de `0007` con un sitio sin coordenadas.
  - **P-panel-7 en sitios**: no hace falta cambio, porque `ResolverQRView` ya hace prefetch. Lo cierra T2.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_planos.PlanoTests.test_reemplazar_imagen_borra_la_anterior --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_models.PuntoControlTests.test_reemplazar_foto_borra_la_anterior --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_models.PuntoControlTests.test_no_desactiva_el_ultimo_punto_y_reactivar_sitio_reactiva --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api.AltaPuntoTests.test_foto_enorme_da_400_sin_500 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api.AltaPuntoTests.test_demasiados_campos_da_400 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api.AltaPuntoTests.test_alta_guarda_precision_m --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api.ModoCampoTests.test_altas_usan_cupo_alta_campo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api.MisPuntosTests.test_sitio_fuera_de_rango_da_400 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel.PuntoPanelTests.test_aviso_punto_fijado_por_escaneo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_admin.PuntoControlAdminTests.test_sitio_y_foto_de_solo_lectura_al_editar --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_admin.PlanoAdminTests.test_sitio_de_solo_lectura_al_editar --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_services.FijarUbicacionTests.test_fijar_ubicacion_bloquea_la_fila --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_migraciones.QuitarPropuestaTests.test_sitio_sin_coordenadas_aplica --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_migraciones.UbicacionFijadaTests.test_backfill_desde_historial --keepdb`
  - `[grep-0]` `grep -n '"crear_visita"' apps/sitios/api_views.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 650 --subtarea T3`

### T4 — Integración ola 1 (principal)

- **Ola**: 1 · **Depende de**: T1, T2, T3
- **Pasos**:
  1. Correr `verificador` y `verificador-b` sobre T2 y T3, con `refutador` si discrepan.
  2. Revisar `cambios.sh` de cada worktree.
  3. Integrar T3 y después T2 con `worktree-integrar.sh` y sus rutas.
  4. Correr `auditor-seguridad` sobre los bloqueos y roles de T2 y los archivos, el límite de pedido y la geolocalización de T3. Las correcciones van en `T2b`/`T3b`, dentro de su presupuesto.
  5. Crear los worktrees de T5 y T6 desde `plan/robustez-datos`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`).
- **Criterios**:
  - `[cmd]` `git log --oneline plan/robustez-datos | grep -q "T2: integra robustez-datos-T2"`
  - `[cmd]` `git log --oneline plan/robustez-datos | grep -q "T3: integra robustez-datos-T3"`

### T5 — C · Panel transversal: tablero, mapa, cargar_demo y MEDIA de tests

- **Ola**: 2 · **Depende de**: T4
- **Worktree**: sí (`worktrees/robustez-datos-T5`)
- **Puede tocar**: `apps/panel/tablero.py`, `apps/panel/mapa.py`, `apps/panel/management/commands/cargar_demo.py`, `apps/panel/templates/panel/tablero.html`, `apps/panel/tests/**`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/panel/urls.py`, `apps/visitas/**`, `apps/sitios/**`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § Panel
- **Presupuesto**: 300 líneas agregadas
- **Qué hacer**:
  - **P-cierre-puntos-13, -14**: el contador de incidencias de ubicación y el `Max` de "Última visita" filtran `cuenta_como_servicio=True`.
  - **P-puntos-control-32**: `cargar_demo` registra los archivos de plano que crea y los borra en un `except` si falla la transacción.
  - **P-puntos-control-33**: el atraso de la demo se acota a `ATRASO_MAXIMO_HORAS - 1 h`, y la idempotencia mira las visitas realizadas, no `exists()`.
  - **P-puntos-control-35**: `test_recorrido` crea su `MEDIA_ROOT` en `setUpClass` (no al importar el módulo) y lo borra.
  - El test del tablero abre la visita de un administrador con `abrir_visita` real, para cruzar con T2.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_tablero.TableroTests.test_excluye_administradores_del_contador --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_mapa.MapaTests.test_ultima_visita_ignora_administradores --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_cargar_demo.CargarDemoTests.test_falla_tardia_no_deja_planos_huerfanos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_cargar_demo.CargarDemoTests.test_atraso_acotado_al_maximo --keepdb`
  - `[grep-0]` `grep -n "^MEDIA_RECORRIDO = tempfile.mkdtemp" apps/panel/tests/test_recorrido.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 --subtarea T5`

### T6 — Visitas: el escaneo registra quién y cuándo fijó la ubicación

- **Ola**: 2 · **Depende de**: T4
- **Worktree**: sí (`worktrees/robustez-datos-T6`)
- **Puede tocar**: `apps/visitas/services.py`, `apps/visitas/tests/test_ubicacion.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/sitios/**`, `apps/panel/**`, migraciones
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § Prohibiciones
- **Presupuesto**: 80 líneas agregadas
- **Qué hacer**: `_fijar_ubicacion_por_escaneo` llena `ubicacion_fijada_por = empleado` y `ubicacion_fijada_en = timezone.now()`. El orden de bloqueo del contrato no cambia.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_ubicacion.UbicacionTests.test_escaneo_registra_quien_y_cuando_fijo --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 80 --subtarea T6`

### T7 — Integración ola 2 y cierre (principal)

- **Ola**: 2 · **Depende de**: T5, T6
- **Pasos**:
  1. Correr `verificador` y `verificador-b` sobre T5 y T6.
  2. Integrar T6 y después T5.
  3. Correr `auditor-seguridad` sobre el plan entero (bloqueos de A, archivos de B).
  4. Escribir en `### Cierra` una línea `- cierra:` por cada uno de los 28 pendientes más P-cierre-puntos-2.
  5. Correr `verificador TODO`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`).
- **Criterios**:
  - `[cmd]` `git log --oneline plan/robustez-datos | grep -q "T5: integra robustez-datos-T5"`
  - `[cmd]` `git log --oneline plan/robustez-datos | grep -q "T6: integra robustez-datos-T6"`
  - `[cmd]` `test "$(py -3 .claude/hooks/pendientes.py --etiqueta robustez-datos --json | py -3 -c 'import json,sys; print(len(json.load(sys.stdin)["abiertos"]))')" -eq 0`
  - `[cmd]` `test "$(py -3 .claude/hooks/pendientes.py --json | py -3 -c 'import json,sys; print(sum(p["id"] == "P-cierre-puntos-2" for p in json.load(sys.stdin)["abiertos"]))')" -eq 0`

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-07-robustez-datos.md robustez-datos`

## Registro de verificación

commit_base: <hash del commit docs(plan): robustez-datos>

### Estado de subtareas
| Tarea | Estado |
|---|---|
| T1 | pendiente |
| T2 | pendiente |
| T3 | pendiente |
| T4 | pendiente |
| T5 | pendiente |
| T6 | pendiente |
| T7 | pendiente |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| | T1 | | | |
| | T2 | | | |
| | T3 | | | |
| | T5 | | | |
| | T6 | | | |
| | TODO | | | |

## Pendientes que deja este plan

### Problemas

### Decisiones
- 2026-10-07 — Al reactivar un sitio se reactivan solo los puntos que apagó el sitio (última fila histórica "Sitio desactivado") — P-puntos-control-27, decisión del usuario al planificar — reemplaza a: (nada)
- 2026-10-07 — `Visita.cuenta_como_servicio` guarda el rol al abrir; `visitas.0009` lo llena con el rol actual del empleado — P-cierre-puntos-10, decisión del usuario al planificar — reemplaza a: (nada)
- 2026-10-07 — El orden de bloqueo único es Proyecto → Visita → PuntoControl — P-puntos-control-9 — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-07 — Las altas de campo (sitio, punto, ubicación) usan el cupo `alta_campo` de 300/h — P-cierre-puntos-11 — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-07 — Un pedido de alta de punto demasiado grande responde 400, no 413, para no cambiar el contrato actual de esa vista — P-cierre-puntos-5 — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-07 — El aviso "punto fijado por escaneo" va en la pestaña de puntos de la ficha del sitio y en la edición del punto, porque no existe una ficha propia del punto; los campos nuevos no se exponen en la API — P-auditoria-p31-1 — reemplaza a: (nada) — decidida por Claude, revisable
- 2026-10-07 — P-cierre-puntos-2 (etiqueta `robustez-panel`) entra en este plan porque el usuario lo pidió en forma explícita — reemplaza a: (nada) — decidida por Claude, revisable

### Cierra
(se completa en T7)

