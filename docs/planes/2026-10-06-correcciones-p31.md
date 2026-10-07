# Plan: Correcciones de la prueba en navegador (P-31)

<!-- Aprobado por el usuario el 2026-10-06. El usuario confirmó la decisión 5 (aplicar las propuestas pendientes) y aprobó la excepción de propiedad 1. juez-plan corrió sobre el borrador: 1 bloqueante (grep-0 de T3 contra test_migraciones.py) y 5 observaciones, resueltos abajo. -->

- **slug**: `correcciones-p31`
- **fecha**: 2026-10-06
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): correcciones-p31`. Se anota en `## Registro de verificación`.
- **objetivo**: corregir los seis problemas que encontró el usuario en la prueba en navegador de `cierre-puntos` (P-puntos-control-31): alta y ubicación de puntos en el plano con modo explícito, arrastre que no vuelve atrás, pestaña Mapa con la ubicación del sitio, acentos en la imagen del QR, y error claro ante una hora futura en la visita manual. Además, aplicar la decisión nueva: el primer escaneo de cualquier usuario fija las coordenadas del punto, sin propuestas.
- **fuera de alcance**: mapa general del panel (`apps/panel/mapa*`), API nueva (ninguna ruta cambia), informes, los pendientes P-cierre-puntos-1 a 15 que no se nombran acá.
- **áreas**: dominio (visitas, sitios), panel, JS del panel, migración de `sitios`
- **seguridad**: sí — geolocalización (un empleado pasa a fijar coordenadas de puntos) y borrado de datos de ubicación (`ubicacion_propuesta`). Corre `auditor-seguridad` en T4.

## Contexto

En la prueba en navegador (paso 4 de T9 de `cierre-puntos`) el usuario reportó seis problemas. Los exploradores encontraron estas causas:

1. **El clic en el plano siempre crea un punto.** `apps/sitios/static/sitios/plano_editor.js:96-111` engancha `mapa.on("click")` y muestra el formulario oculto `#plano-alta` de `_pestana_planos.html:15-25`. No existe ningún "modo".
2. **El punto arrastrado vuelve a su lugar.** `plano_editor.js:55-73` llama a `htmx.ajax(..., {handler})`. Con htmx 2.0.11, un `handler` propio reemplaza al manejador por defecto, que es el único que asigna `respuesta.successful`. Ese valor queda `undefined`, el JS toma la rama de error y hace `setLatLng` a la posición vieja, aunque el servidor guardó (200 JSON de `PuntoPosicion`, `panel_views.py:285-294`). El mismo bug está en `puntos_mapa.js:76-77`.
3. **La pestaña Mapa muestra los puntos, no el sitio.** `_pestana_mapa.html` y `puntos_mapa.js` dibujan los puntos, el selector para fijar lat/lng con un clic (`PuntoUbicacion`) y la lista de propuestas (`PuntoPropuesta`). El sitio solo se ve en su formulario de edición (`formulario.html` con `sitio_mapa.js` y el geocodificador).
4. **No hay forma de ubicar en el plano un punto existente.** `_datos_plano` (`panel_views.py:160-178`) filtra los puntos sin ese plano, y `PuntoPosicion` responde 400 si `not punto.plano_id`. Hoy solo se puede escribiendo x/y a mano en Editar punto.
5. **La ó de "Depósito" no aparece en el QR.** `apps/sitios/qr.py:30` usa `ImageFont.load_default(size=22)`, la Aileron recortada que trae Pillow 12.3, sin glifos acentuados. `static/fonts/barlow-latin-600-normal.woff2` (OFL) sí los tiene, y Pillow la lee directamente.
6. **"La fecha de cierre no puede ser futura." en la visita manual.** El usuario cargó 17:50 a las 17:30. `registrar_visita_manual` (`apps/visitas/services.py:630`) no valida la hora futura. El corte salta adentro de `cerrar_visita` (`:584`, tolerancia de 10 min) como error general que menciona el "cierre". `FormularioManual` (`apps/visitas/panel_forms.py:107`) no tiene valor inicial ni `max`.

**Decisiones del usuario al planificar** (van a `### Decisiones`):
1. El primer escaneo de un punto sin coordenadas, sea de un empleado o de un administrador, las fija directamente, con precisión de hasta `PRECISION_MAXIMA_M` (50 m). Desaparecen la ubicación propuesta y el Aceptar/Descartar. **Reemplaza a**: la decisión del 2026-10-06 de `puntos-control` ("…o las propone el primer escaneo de un empleado… y el administrador las acepta") y a la decisión 2 de `cierre-puntos` en lo que dice "Empleado: sigue proponiendo".
2. La pestaña Mapa de la ficha del sitio muestra solo la ubicación del sitio (de solo lectura, con un enlace "Editar ubicación" al formulario del sitio). La ubicación geográfica de los puntos no se edita en esa pestaña: la fija el primer escaneo, y se puede corregir en Editar punto (que ya tiene latitud y longitud).
3. Plano: botón "Crear nuevo punto" que activa un modo de alta, y una lista "Sin ubicar en este plano" con un botón "Ubicar" por punto que activa un modo de ubicación. En los dos casos, el siguiente clic en el plano hace la acción. Escape o el mismo botón cancelan el modo.
4. Visita manual: una hora más de 10 minutos posterior a la actual se rechaza en el propio campo, con el texto "La fecha y hora de la visita no puede ser posterior a la hora actual.". El campo viene cargado con la hora actual y lleva `max`.
5. Las propuestas pendientes al momento de la migración se aplican (fijan lat/lng) si el punto sigue sin coordenadas, porque ya cumplían la precisión. Después se elimina el campo.

**Tests de planes anteriores que cambian por la decisión 1** (los reemplaza este plan; sus criterios en `puntos-control` y `cierre-puntos` ya se verificaron en sus HEAD):
- `apps.visitas.tests.test_ubicacion.UbicacionTests.test_empleado_solo_propone` (criterio de T3 de cierre-puntos) pasa a ser `test_empleado_fija_coordenadas_del_punto`.
- `apps.visitas.tests.test_services.CicloVisitaTests.test_revision_propone_ubicacion_solo_sin_coordenadas_y_precisa` (puntos-control) pasa a ser `test_revision_fija_ubicacion_solo_sin_coordenadas_y_precisa`.
- `apps.sitios.tests.test_panel.PuntoPanelTests.test_aceptar_ubicacion_propuesta` y `test_fijar_ubicacion_valida_el_rango` (puntos-control) se eliminan, junto con sus vistas.
- `apps.api.tests.test_flujo.ModoCampoFlujoTests.test_administrador_crea_y_empleado_escanea_sin_propuesta` (T8 de cierre-puntos) conserva el nombre y deja de leer `ubicacion_propuesta`.

**Excepciones de propiedad** (aprobadas por el usuario el 2026-10-06; ninguna corre en paralelo con el dueño):
1. T3 (sitios, ola 2) edita `apps/api/tests/test_flujo.py`, solo la aserción sobre `ubicacion_propuesta` de `ModoCampoFlujoTests`, con T1 ya integrada.

## Contrato entre subtareas (fijo)

- **T1 (visitas)**: `_fijar_ubicacion_por_escaneo(punto, revision, usuario)` se usa para cualquier rol. Lo que se pierde es `_proponer_ubicacion`, y la función deja de escribir `ubicacion_propuesta`. `_change_reason = "Ubicación fijada por el primer escaneo"`. Después de T1, ningún archivo de `apps/visitas` nombra `ubicacion_propuesta`.
- **T2 (sitios, plano y QR)**: `services.ubicar_en_plano(punto, plano, x, y)` valida que el plano sea del mismo sitio y que x e y estén entre 0 y 1, y guarda `plano`, `x` e `y`. `mover_en_plano` se mantiene. `PuntoPosicion` acepta un `plano` opcional en el POST y, si viene, usa `ubicar_en_plano`. `_datos_plano` suma `sin_ubicar: [{id, nombre, url}]` con los puntos activos del sitio que no tienen plano, o que tienen este plano sin x/y. Los manejadores de `htmx.ajax` miran `respuesta.xhr.status` (2xx).
- **T3 (sitios, propuestas y Mapa)**: migración `sitios/0007` que aplica las propuestas pendientes y quita `PuntoControl.ubicacion_propuesta`. Se van `aceptar_ubicacion_propuesta`, `descartar_ubicacion_propuesta`, `PuntoPropuesta`, `PuntoUbicacion`, `UbicacionForm`, sus rutas y `puntos_mapa.js`. La pestaña Mapa usa un `sitio_ficha_mapa.js` nuevo, de solo lectura y con un marcador.

## Olas

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1 (visitas) ∥ T2 (sitios: plano y QR) | — |
| 2 | T3 (sitios: propuestas fuera y pestaña Mapa), T4 (integración, auditoría, navegador, TODO) | sitios (0007) |

T3 va después de T1 porque `apps/visitas/services.py` escribe `ubicacion_propuesta` hasta que T1 lo quita. T3 va después de T2 porque las dos tocan `panel_views.py`, `panel_urls.py`, `services.py` y `test_panel.py` de `sitios`.

## Subtareas

### T1 — Visitas: el primer escaneo fija coordenadas; hora futura en la visita manual

- **Ola**: 1 · **Depende de**: —
- **Puede tocar**: `apps/visitas/services.py`, `apps/visitas/panel_forms.py`, `apps/visitas/templates/visitas/panel/manual.html`, `apps/visitas/tests/test_ubicacion.py`, `apps/visitas/tests/test_services.py`, `apps/visitas/tests/test_panel.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/sitios/**`, `apps/api/**`, modelos y migraciones
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Services y § Forms
- **Worktree**: sí
- **Ruta**: delegada (implementador)
- **Presupuesto**: 250 líneas agregadas
- **Qué hacer**:
  - `_guardar_revision` (usada por `registrar_revision`) llama a `_fijar_ubicacion_por_escaneo(punto, revision, empleado)` para cualquier rol. Se elimina `_proponer_ubicacion`, y se quitan la línea `ubicacion_propuesta = None` y ese campo del `update_fields`. El docstring y el motivo del historial se ajustan.
  - `registrar_visita_manual` valida `realizada_en > timezone.now() + TOLERANCIA_FUTURO` antes de crear nada y lanza `ValidationError({"realizada_en": "La fecha y hora de la visita no puede ser posterior a la hora actual."})`. La vista ya traduce `error_dict` a errores de campo; confirmarlo con el test.
  - `FormularioManual.realizada_en`: valor inicial `timezone.localtime()` en el formato del widget y atributo `max` con la hora local actual, los dos calculados en `__init__`.
  - Renombrar y adaptar los tests de la lista "Tests de planes anteriores".
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_ubicacion.UbicacionTests.test_empleado_fija_coordenadas_del_punto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.CicloVisitaTests.test_revision_fija_ubicacion_solo_sin_coordenadas_y_precisa --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.ManualPorPuntosTests.test_hora_futura_se_rechaza_en_el_campo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel.ManualTests.test_hora_futura_marca_el_campo_y_viene_cargada_la_actual --keepdb`
  - `[grep-0]` `grep -rn "ubicacion_propuesta\|_proponer_ubicacion" apps/visitas --include=*.py --include=*.html --include=*.js`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 --subtarea T1`

### T2 — Sitios: modos del plano, arrastre que guarda, ubicar puntos existentes, acentos del QR

- **Ola**: 1 · **Depende de**: —
- **Puede tocar**: `apps/sitios/static/sitios/plano_editor.js`, `apps/sitios/static/sitios/puntos.css`, `apps/sitios/templates/sitios/panel/_pestana_planos.html`, `apps/sitios/panel_views.py`, `apps/sitios/panel_forms.py`, `apps/sitios/services.py`, `apps/sitios/qr.py`, `apps/sitios/tests/test_panel.py`, `apps/sitios/tests/test_qr.py` (nuevo), `apps/sitios/tests/test_services.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/sitios/models.py`, `apps/sitios/migrations/**`, `apps/sitios/api_*.py`, `apps/sitios/templates/sitios/panel/_pestana_mapa.html`, `apps/sitios/static/sitios/puntos_mapa.js`, `apps/visitas/**`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § Panel
- **Worktree**: sí
- **Ruta**: delegada (implementador)
- **Presupuesto**: 350 líneas agregadas
- **Qué hacer**:
  - En `plano_editor.js`, un estado `modo` que puede ser `null`, `{tipo: "alta"}` o `{tipo: "ubicar", punto}`. Con `modo` nulo, el clic en el plano no hace nada. El botón "Crear nuevo punto" activa o desactiva el alta. "Ubicar" activa la ubicación. Escape cancela. El cursor y un texto visible indican el modo activo. Los marcadores frenan la propagación del clic (`L.DomEvent.stopPropagation`).
  - En `guardar`, y en el nuevo `ubicar`, el éxito se decide por `respuesta.xhr.status` entre 200 y 299. Al ubicar con éxito se recarga la pestaña del plano.
  - `_pestana_planos.html`: el botón "Crear nuevo punto", la lista "Sin ubicar en este plano" con un "Ubicar" por punto y un texto de ayuda nuevo. Todo sin `<script>` en línea; los datos pasan por `json_script`.
  - `_datos_plano` suma `sin_ubicar`. `PuntoPosicion` acepta `plano`. Nuevo `services.ubicar_en_plano`.
  - `qr.py`: la fuente es `ImageFont.truetype(BASE_DIR / "static/fonts/barlow-latin-600-normal.woff2", 22)`, con una constante de ruta.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel.PlanoPanelTests.test_ubicar_punto_sin_plano_con_clic --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel.PlanoPanelTests.test_plano_ofrece_crear_y_lista_sin_ubicar --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel.PlanoPanelTests.test_ubicar_en_plano_de_otro_sitio_da_400 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_qr.QrTests.test_dibuja_letras_acentuadas --keepdb`
  - `[grep-0]` `grep -n "respuesta.successful" apps/sitios/static/sitios/plano_editor.js`
  - `[grep-1]` `grep -n "xhr.status" apps/sitios/static/sitios/plano_editor.js`
  - `[grep-0]` `grep -n "load_default" apps/sitios/qr.py`
  - `[cmd]` `node --check apps/sitios/static/sitios/plano_editor.js`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios apps.panel --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 350 --subtarea T2`

`test_dibuja_letras_acentuadas` dibuja "ó" y "o" con la fuente de `qr.py` y comprueba que los mapas de bits son distintos y que "ó" no es igual al glifo de un carácter inexistente (por ejemplo "中"). Ese es el defecto que reproduce.

### T3 — Sitios: fuera las propuestas; la pestaña Mapa muestra el sitio

- **Ola**: 2 · **Depende de**: T1 y T2 integradas
- **Puede tocar**: `apps/sitios/models.py`, `apps/sitios/migrations/0007_*.py`, `apps/sitios/services.py`, `apps/sitios/panel_views.py`, `apps/sitios/panel_urls.py`, `apps/sitios/panel_forms.py`, `apps/sitios/templates/sitios/panel/_pestana_mapa.html`, `apps/sitios/templates/sitios/panel/ficha.html`, `apps/sitios/static/sitios/puntos_mapa.js` (se borra), `apps/sitios/static/sitios/sitio_ficha_mapa.js` (nuevo), `apps/sitios/tests/test_panel.py`, `apps/sitios/tests/test_models.py`, `apps/sitios/tests/test_api.py`, `apps/sitios/tests/test_services.py`, `apps/sitios/tests/test_migraciones.py`, `apps/api/tests/test_flujo.py` (excepción 1)
- **No puede tocar**: `docs/planes/`, `config/`, `apps/visitas/**`, `apps/sitios/api_*.py`, `apps/sitios/serializers.py`, `docs/api/openapi-v1.yaml`
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Models y § Migrations; `.claude/skills/convenciones-proyecto/SKILL.md` § Panel
- **Worktree**: sí
- **Ruta**: delegada (implementador)
- **Presupuesto**: 300 líneas agregadas
- **Qué hacer**:
  - Migración `0007` con un `RunPython` que, para cada punto con `ubicacion_propuesta` y sin lat/lng, copia la propuesta a lat/lng. El reverso no hace nada. Después, `RemoveField`. El historial ya excluía el campo: quitarlo de `excluded_fields`.
  - Borrar los servicios de propuesta, `PuntoPropuesta`, `PuntoUbicacion`, `UbicacionForm`, sus rutas, `con_propuesta` del contexto y `puntos_mapa.js`. `fijar_ubicacion` y `fijar_ubicacion_en_campo` dejan de limpiar la propuesta.
  - `_datos_mapa` devuelve solo `{"sitio": {nombre, lat, lng}}`. `_pestana_mapa.html`: título "Ubicación del sitio", el mapa con un marcador si hay coordenadas o el texto "El sitio no tiene ubicación cargada." si no las hay, el enlace "Editar ubicación" a `sitio_editar`, y la atribución de OSM que ya está. `ficha.html` carga `sitio_ficha_mapa.js` en la pestaña mapa.
  - Ajustar los tests de la lista "Tests de planes anteriores". `test_ficha_muestra_atribucion_osm` sigue en verde.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel.SitioPanelTests.test_pestana_mapa_muestra_el_sitio_y_no_los_puntos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_migraciones.QuitarPropuestaTests.test_propuesta_pendiente_se_aplica_si_no_hay_coordenadas --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel.SitioPanelTests.test_ficha_muestra_atribucion_osm --keepdb`   # guarda de regresión: el test ya existe
  - `[grep-0]` `grep -rn "ubicacion_propuesta\|punto_propuesta\|punto_ubicacion" apps --include=*.py --include=*.html --include=*.js --exclude-dir=migrations --exclude=test_migraciones.py`
  - `[no-existe]` `apps/sitios/static/sitios/puntos_mapa.js`
  - `[cmd]` `node --check apps/sitios/static/sitios/sitio_ficha_mapa.js`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios apps.visitas apps.api --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 --subtarea T3`

### T4 — Integración, contrato, auditoría, navegador y verificación TODO (principal)

- **Ola**: 2 · **Depende de**: T1, T2, T3
- **Pasos**:
  1. `verificador` y `verificador-b` por subtarea (`refutador` si discrepan). Integrar T1 y T2, crear T3 desde la rama del plan, verificarla e integrarla.
  2. Commit `T4: docs de arquitectura`: `docs/01-modelo-y-arquitectura.md` deja de describir `ubicacion_propuesta` y el aceptar/descartar (líneas 55 y 153), según las decisiones 1 y 2.
  3. `manage.py spectacular --validate`. Si el YAML cambia, commit `T4: contrato openapi`. No debería cambiar, porque ningún serializer exponía la propuesta.
  4. `auditor-seguridad` sobre la decisión 1 (fijado por un empleado, migración de datos de ubicación) el editor del plano (`PuntoPosicion` con `plano`) y la generación del QR (`apps/sitios/qr.py`, fuente nueva).
  5. Prueba en navegador del usuario: los seis puntos del reporte más el recorrido de P-31. Este OK vale también como el paso 4 de T9 de `cierre-puntos`.
  6. Verificación TODO de este plan y de `cierre-puntos` (en su HEAD `9728a27`), cada una con `verificador` y `verificador-b`.
- **Presupuesto**: 1500 líneas agregadas en commits `T4:` (docs de arquitectura y, si cambia, el YAML)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/correcciones-p31 | grep -q "T1: integra correcciones-p31-T1"`
  - `[cmd]` `git log --oneline plan/correcciones-p31 | grep -q "T2: integra correcciones-p31-T2"`
  - `[cmd]` `git log --oneline plan/correcciones-p31 | grep -q "T3: integra correcciones-p31-T3"`
  - `[cmd]` `T=$(mktemp) && PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file "$(cygpath -w "$T")" && diff -q --strip-trailing-cr "$T" docs/api/openapi-v1.yaml; r=$?; rm -f "$T"; exit $r`
  - `[grep-0]` `grep -n "ubicacion_propuesta\|ubicación propuesta" docs/01-modelo-y-arquitectura.md`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 1500 --subtarea T4`

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-06-correcciones-p31.md correcciones-p31`

## Verificación de punta a punta

- Los criterios de arriba, con `verificador` y `verificador-b`.
- En el navegador (`cargar_demo` + `runserver`, usuario `demo-admin`):
  1. **Plano:** el clic sin modo no hace nada. "Crear nuevo punto" seguido de un clic da de alta. Un punto arrastrado queda donde se soltó, sin el aviso de error. Un punto creado con el formulario aparece en "Sin ubicar", y "Ubicar" seguido de un clic lo coloca.
  2. **Pestaña Mapa:** muestra solo el marcador del sitio y el enlace "Editar ubicación".
  3. **QR:** al descargar el de un punto de "Depósito Demo Sur", se lee "Depósito".
  4. **Visita manual:** con una hora 20 minutos posterior, el error aparece en el campo. El campo viene cargado con la hora actual y guarda.
  5. **Escaneo de un empleado:** `registrar_revision_demo` sobre un punto sin coordenadas las fija (si la precisión alcanza).

## Registro de verificación

commit_base: 6510a35

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | hecha (integrada 2f4ad1b) |
| T2 | hecha (integrada 16cec24) |
| T3 | hecha (integrada 9ac7257) |
| T4 | hecha |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| 2026-10-06 | T1 (verificador) | 556d341 | PASA 7/7 | worktree correcciones-p31-T1 |
| 2026-10-06 | T1 (verificador-b) | 556d341 | PASA 7/7 | |
| 2026-10-06 | T2 (verificador) | 0a8cdda | PASA 10/10 | worktree correcciones-p31-T2 |
| 2026-10-06 | T2 (verificador-b) | 0a8cdda | PASA 10/10 | |
| 2026-10-06 | T3 (verificador) | 91b2773 | PASA 9/9 | worktree correcciones-p31-T3 |
| 2026-10-06 | T3 (verificador-b) | 91b2773 | PASA 9/9 | |
| 2026-10-06 | T4 paso 3: spectacular --validate | 9ac7257 | sin cambios | el YAML no cambia (diff=0) |
| 2026-10-06 | T4 paso 4: auditor-seguridad | 9ac7257 | 0 bloqueantes, 2 importantes, 1 menor, 3 observaciones | todo a pendientes por decisión del usuario |
| 2026-10-07 | T4 paso 5: prueba en navegador | 3832274 | OK del usuario | plano (modos, arrastre, ubicar), pestaña Mapa, QR con acentos, visita manual con hora futura, `registrar_revision_demo` fija coordenadas (historial: demo-empleado, "Ubicación fijada por el primer escaneo"); vale también para T9 paso 4 de `cierre-puntos` |
| 2026-10-07 | TODO (verificador) | 0f43474 | PASA 38/38 | suite completa 516 tests OK; contrato intacto |
| 2026-10-07 | TODO (verificador-b) | 0f43474 | PASA 38/38 | |

## Pendientes que deja este plan

### Problemas

- P-correcciones-p31-1 [importante] El primer escaneo fija las coordenadas del punto aunque la revisión tenga `incidencia_ubicacion` (`apps/visitas/services.py`, `_fijar_ubicacion_por_escaneo`; la precisión la declara el cliente): un empleado puede anclar un punto lejos del sitio y desde ahí sus revisiones dan distancia ≈ 0 sin incidencia. Corrección propuesta: no fijar si `revision.incidencia_ubicacion`, con un test (empleado a más de `DISTANCIA_MAXIMA_M` → `latitud is None`). Si el sitio no tiene coordenadas, el escaneo fija igual (decisión del usuario del 2026-10-06). Auditoría T4.
- P-correcciones-p31-2 [importante] La migración `sitios/0007` aplica las propuestas pendientes sin crear una fila en `HistoricalPuntoControl` y pierde `propuesta["revision"]` (quién originó la coordenada). Corrección propuesta: crear la fila histórica en el `RunPython`, con un motivo que cite la revisión, y saltear las propuestas cuya revisión tuvo `incidencia_ubicacion`. **Hay que resolverlo antes de aplicar 0007 en producción**: después el dato se pierde. Auditoría T4.
- P-correcciones-p31-3 [menor] El docstring de `registrar_revision` (`apps/visitas/services.py`) sigue diciendo que el empleado propone y el administrador fija. Auditoría T4.
- P-correcciones-p31-4 [observación] La migración `0007` aborta ante una propuesta con `NaN` o fuera de rango (`Decimal` no levanta en la conversión, falla en `save()`); solo con datos manipulados. Auditoría T4.
- P-correcciones-p31-5 [observación] `PuntoPosicion` (`apps/sitios/panel_views.py`): `isdigit()` deja pasar dígitos Unicode (`²`) que dan 500, y acepta planos inactivos con un POST armado a mano; usar `ModelChoiceField(Plano.objects.filter(activo=True))` en `PosicionForm`. Solo administradores. Auditoría T4.
- P-correcciones-p31-6 [observación] `apps/sitios/qr.py` lee una `.woff2`, que exige FreeType con brotli, y Pillow no tiene la versión fijada en `requirements.txt`: si en producción falta, la descarga del QR da 500. Alternativas: fijar Pillow, versionar un TTF o volver a `load_default` con un aviso en el log. Auditoría T4.

### Decisiones

- 2026-10-06 — El primer escaneo de un punto sin coordenadas, sea de un empleado o de un administrador, las fija directamente con precisión de hasta `PRECISION_MAXIMA_M`; desaparecen la ubicación propuesta y el Aceptar/Descartar — el usuario lo pidió tras la prueba en navegador — reemplaza a: 2026-10-06 (`puntos-control`, el empleado propone y el administrador acepta; y la decisión 2 de `cierre-puntos` en "Empleado: sigue proponiendo")
- 2026-10-06 — La pestaña Mapa de la ficha del sitio muestra solo la ubicación del sitio, de solo lectura con enlace "Editar ubicación"; la de los puntos se corrige en Editar punto — prueba en navegador — reemplaza a: (nada)
- 2026-10-06 — Plano con modos explícitos: "Crear nuevo punto" y "Ubicar" activan un modo; el siguiente clic hace la acción; Escape o el mismo botón cancelan — el clic suelto creaba puntos sin querer — reemplaza a: (nada)
- 2026-10-06 — Visita manual: una hora más de 10 minutos posterior a la actual se rechaza en el campo; el campo viene con la hora actual y `max` — el error salía como "fecha de cierre" — reemplaza a: (nada)
- 2026-10-06 — Las propuestas pendientes al migrar se aplican si el punto sigue sin coordenadas, y después se elimina el campo — ya cumplían la precisión — reemplaza a: (nada)
- 2026-10-06 — Los hallazgos de la auditoría de T4 quedan como pendientes (P-correcciones-p31-1 a 6), sin corregir en este plan; si se corrige el 1, con el sitio sin coordenadas el escaneo de un empleado fija igual — decisión del usuario — reemplaza a: (nada)

### Cierra

<!-- Al cerrar: P-puntos-control-31 (con el OK del navegador); P-puntos-control-15 (retención de ubicacion_propuesta: el campo deja de existir). -->
