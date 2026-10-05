# Propuesta: puntos de control, planos y seguimiento en tiempo real

Fecha: 2026-10-05. Estado: aprobada por el usuario tras conversación con la empresa; se ejecuta con el plan `puntos-control`. Reemplaza el "un QR por sitio" de `docs/01-modelo-y-arquitectura.md` §3.2 y las decisiones del 2026-09-29 y 2026-10-02 sobre el QR.

## Requisito

- En un sitio hay de uno a muchos **puntos de revisión** (estaciones cebaderas, salas de máquinas, sectores), cada uno con su QR. Un sitio chico tiene un solo punto.
- El sitio puede tener uno o más **planos** (imágenes que entrega el cliente) con un marcador por punto. El marcador refleja la última revisión y se actualiza mientras el operario recorre el lugar.
- El **administrador** ve en el mapa los sitios y sus proyectos; desde la ficha del sitio ve los planos con sus marcadores.
- El **operario** ve, al escanear un QR, el plano del punto si existe (opcional), y en el mapa normal todos los puntos geolocalizados.

## Modelo

### `sitios.PuntoControl` (nuevo)
- `sitio` FK, `nombre`, `sector` (texto libre, opcional), `orden`, `activo`
- `qr_codigo` UUID único, `editable=False`, con default; `qr_impreso_el` opcional (se mueve desde Sitio)
- `plano` FK opcional a `Plano`; `x`, `y` fracciones 0–1 de la imagen (Decimal 5,4); nulos si no está ubicado
- `latitud`, `longitud` opcionales; `ubicacion_propuesta` (JSON opcional: lat, lng, precisión, revisión de origen) que el administrador acepta o descarta
- Historial con `django-simple-history`
- Restricción: un punto activo tiene `sitio` activo; al desactivar un sitio se desactivan sus puntos

`Sitio.qr_codigo` desaparece. **Migración de datos**: por cada sitio se crea un punto "General" (`orden=0`) con su `qr_codigo` y `qr_impreso_el` actuales; los QR ya impresos siguen resolviendo.

### `sitios.Plano` (nuevo)
- `sitio` FK, `nombre` ("Planta baja", "Techo"), `imagen` (JPG/PNG; PDF convertido a imagen al subir, primera página), `ancho_px`, `alto_px`, `orden`, `activo`
- Las imágenes se sirven solo por vistas autenticadas (panel y API), nunca desde `MEDIA_URL` abierto, igual que las fotos

### `visitas.Visita` (cambia de significado)
Pasa a ser **la jornada de un empleado sobre un proyecto en un sitio**: se abre con el primer escaneo del día (o la asignación), acumula revisiones y se cierra.
- Nuevos: `abierta_en`, `cerrada_en`, `cierre` (choices: `empleado`, `sistema`, `administrador`)
- `estado` incorpora `abierta` entre `pendiente` y `realizada`
- Conservan su significado: `origen`, `motivo_manual`, `programada_para`, `asignada_por`, `incidencia_*`, `observaciones`, `datos` y `esquema_planilla` (ahora solo los campos de ámbito `visita`)
- Dejan de vivir en Visita y pasan a Revisión: `latitud`, `longitud`, `precision_m`, `cliente_uuid`, `recibida_en`, `realizada_en` (en Visita queda `cerrada_en`), las fotos y los productos aplicados
- `realizada_en` se mantiene como propiedad = `cerrada_en`, para no romper certificados ni historial

### `visitas.Revision` (nuevo)
Cada escaneo: `visita` FK, `punto` FK, `realizada_en` (del teléfono), `recibida_en`, `cliente_uuid` único, `latitud`, `longitud`, `precision_m`, `datos` y `esquema_planilla` (ámbito `punto`), `observaciones`, `incidencia`, `incidencia_detalle`, `orden` dentro de la visita. `Foto` y `ProductoAplicado` pasan a colgar de Revisión (FK renombrada en migración; las filas existentes se reasignan a una revisión "General" creada por la migración de datos).

Reglas (en `services.py`):
- Una revisión desde la app exige QR válido de un punto activo, coordenadas y ≥1 foto; límite de atraso `ATRASO_MAXIMO_HORAS`; idempotencia por `cliente_uuid`.
- Un punto puede revisarse más de una vez en la misma visita (la última manda para el semáforo; todas quedan).
- `cerrar_visita(visita, quien)` fija `cerrada_en`, `cierre`, estado `realizada`, y actualiza el proyecto (`encargado_actual`, `actualizado`, `proxima_visita`) como hoy hace `registrar_visita_realizada`.
- Cierre automático: comando de gestión `cerrar_visitas_abiertas` (cron diario) cierra con `cierre=sistema` las abiertas desde hace más de `VISITA_ABIERTA_MAXIMO_HORAS` (default 16).

### `servicios.CampoPlanilla`
- Nuevo `ambito` (choices: `punto`, `visita`; default `punto`). `esquema_planilla(ambito)` filtra por ámbito. Los campos existentes migran a `punto`.

### Estado por punto (propiedad, no columna)
`estado_revision` de un punto para un proyecto: `al_dia`, `proxima`, `vencida`, `sin_revisar`, calculado con la última revisión y `frecuencia_dias` del proyecto; usa el mismo `UMBRAL_PROXIMA_DIAS`. El estado del sitio en el mapa pasa a ser el peor estado de sus puntos.

## API `/api/v1/` (cambia el contrato; regenerar `docs/api/openapi-v1.yaml`)
- `POST qr/<uuid>/resolver/` → punto (nombre, sector, plano: url de imagen autenticada + `x,y` de todos los puntos del plano + estado), sitio, proyectos activos con esquema de planilla de ámbito `punto` y `visita`, visita abierta propia si existe.
- `POST visitas/abrir/` (proyecto; o usa la pendiente asignada) → visita `abierta`.
- `POST revisiones/` (multipart: visita, punto, fotos, planilla, productos, coordenadas, `cliente_uuid`) → 201.
- `POST visitas/<id>/cerrar/` (planilla de ámbito `visita`, observaciones, incidencia) → `realizada`.
- `GET me/visitas/` incluye abiertas y pendientes; `GET me/puntos/?sitio=` para el mapa del operario (puntos activos de los sitios con visitas asignadas o abiertas, con lat/lng).
- `GET planos/<id>/imagen/` autenticada.
- Se eliminan `POST visitas/` (se reemplaza por abrir + revisiones + cerrar).

## Panel
- Ficha de sitio: pestañas Mapa (puntos geolocalizados, clic para fijar lat/lng) y Planos (subir imagen, editor con Leaflet `CRS.Simple`: arrastrar marcadores fija `x,y`; alta de punto desde el plano). Lista de puntos con semáforo, QR por punto (PNG) y hoja de etiquetas (todas las del sitio, para imprimir) cuando entre `informes`.
- Seguimiento: la ficha del sitio y el plano sondean `/panel/sitios/<id>/estado/` con HTMX cada 5 s mientras están abiertos (`hx-trigger="every 5s"`); la respuesta es un parcial con los marcadores. El transporte se encapsula en una sola vista para poder pasar a SSE sin tocar el modelo.
- Mapa general: sin cambios de forma; el color del sitio es el peor estado de sus puntos.
- Ficha de proyecto: línea de tiempo por visita, desplegable con sus revisiones.
- Visita manual: el administrador elige los puntos revisados.
- Ubicaciones propuestas: lista para aceptar o descartar.

## Certificado e informes (plan `informes`)
Enumeran puntos revisados por fecha, con planilla y productos; es lo que exige un programa MIP certificado.

## Olas sugeridas para el plan
1. Modelos y migraciones de datos (`sitios`: PuntoControl, Plano; `servicios`: ámbito; `visitas`: Revision y reasignación) + servicios con tests. Lineal por dependencias entre apps: `servicios` y `sitios` en paralelo, luego `visitas`.
2. API nueva (por app, en paralelo) + regeneración del contrato + comando `cerrar_visitas_abiertas`.
3. Panel: ficha de sitio con mapa de puntos y planos (sitios), revisiones en fichas y visita manual por puntos (visitas), sondeo de estado (panel), QR por punto (sitios) — en paralelo.
4. Integración, recorrido completo, `cargar_demo` con puntos y plano.

## Decisiones que deja escritas
- Punto de control como unidad del QR; el sitio ya no tiene QR propio (migración "General").
- Visita = jornada; Revisión = escaneo. La evidencia (fotos, coordenadas, productos) vive en la revisión.
- Tiempo real por sondeo HTMX de 5 s; SSE queda como evolución posible sin cambio de modelo.
- Los planos son imágenes que entrega el cliente; el sistema no los dibuja.
- Las coordenadas de un punto las fija el administrador; el teléfono solo las propone.
