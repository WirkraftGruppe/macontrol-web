# Plan: cerrar los menores abiertos de fotos, worktrees y plantilla

- **slug**: `menores-abiertos`
- **fecha**: 2026-10-03
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): menores-abiertos`. El hash se anota en `## Registro de verificación`.
- **objetivo**:
  - una foto corrupta, de formato no permitido o demasiado grande para su formato se rechaza, también en el admin con un error de formulario y no con un 500;
  - una visita realizada ya no deja cambiar `programada_para` ni `asignada_por`;
  - los scripts de worktree validan sus argumentos y deshacen un merge que rompe tests;
  - la plantilla de plan no tiene criterios que nadie ejecuta.
- **fuera de alcance**:
  - API, autenticación, HEIC, retención de historial, servir MEDIA autenticado;
  - observaciones de T1 de `paralelismo` (`RE_FECHA_SLUG`, `plan_de_rama`);
  - la junction que queda viva si falla la prueba de humo;
  - cambios de modelo o migraciones.
- **áreas**: dominio (fotos, admin), infraestructura (hooks, plantilla)
- **seguridad**: sí. Toca la subida de fotos (`imagenes.py`, formulario del admin) y los permisos de edición del admin sobre la evidencia. Por eso corre también `auditor-seguridad` sobre T1 y T2.

## Contexto mínimo

- `apps/visitas/imagenes.py:28-33`: `exif_transpose` hace `load()` dentro de un `try/except Exception`. Por eso un PNG con IDAT corrupto o un ICNS se aceptan como imagen gris. `Image.open` acepta cualquier formato, y PNG y WebP de menos de 40 MP pueden ocupar cientos de MB al decodificarse (N1).
- `apps/visitas/models.py:126-128`: `Foto.save` llama a `procesar_imagen`, y su `ValidationError` sube como 500 desde el inline del admin (N4).
- `apps/visitas/admin.py:78-81`: en una visita cerrada, `get_readonly_fields` devuelve `CAMPOS_EVIDENCIA`, que no incluye `programada_para` ni `asignada_por` (N5).
- `.claude/hooks/worktree-integrar.sh:73-89`: el control de alcance compara prefijos de texto, así que `""` acepta todo y `app` acepta `app_v2/`. Las líneas 97-106 dejan el merge hecho si fallan los tests. `worktree-crear.sh:41-53` no valida `rama_base`.
- `docs/plantilla-plan.md:114-122`: hay criterios bajo `### Ola N`. `verificar_plan.py:285-290` corta la tarea en cualquier encabezado, así que esos criterios no se ejecutan, y el `verificador` solo corre `T<n>` y el cierre global.

## Olas

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1, T2, T3, T4 | ninguna. T1 y T2 tocan archivos disjuntos de `apps/visitas`; T3 y T4, archivos disjuntos de `.claude/hooks/` y `docs/`. |

## Subtareas

### T1 — Rechazar fotos corruptas, de formato no permitido o demasiado grandes para su formato

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/visitas/imagenes.py`, `apps/visitas/tests/test_fotos.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/visitas/models.py`, `apps/visitas/admin.py`, `apps/visitas/services.py`, `apps/visitas/migrations/`, `apps/visitas/tests/test_admin.py`, `apps/visitas/tests/test_models.py`, `apps/visitas/tests/test_services.py`, cualquier otra app
- **Skill a leer antes**: `.agents/skills/django-security/SKILL.md` § File Upload Security
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 160 líneas agregadas
- **Qué hacer**:
  - Abrir con `Image.open(archivo, formats=("JPEG", "PNG", "WEBP"))`.
  - Agregar `MAX_PIXELES_POR_FORMATO = {"JPEG": 40_000_000, "PNG": 16_000_000, "WEBP": 16_000_000}` y rechazar según `original.format` antes de decodificar. `MAX_PIXELES` puede quedar como el máximo general o reemplazarse.
  - Orden: tope → `draft` → `original.load()` fuera del `try` → `try: ImageOps.exif_transpose(original, in_place=True)` → `except Exception`, con el mismo comentario. Después, `thumbnail`, `convert` y `save` sobre `original`.
  - El `except` externo sigue capturando `OSError`. El juez comprobó que `load()` sobre un IDAT corrupto lanza `OSError("broken data stream")`, con CRC recalculado o sin él. Si otro caso de los tests lanza otra excepción de decodificación, se agrega al `except` con un comentario.
  - Tests nuevos en `FotoTests`. Los tres fallan antes del cambio y verifican que `Foto.objects.count() == 0`:
    - `test_png_corrupto_se_rechaza`: un PNG real con los bytes de datos del IDAT sobrescritos, en dos `subTest`, uno con CRC recalculado y otro sin recalcular.
    - `test_webp_con_dimensiones_enormes_se_rechaza`: un WebP de 8000×4900, que suma menos de 40 MP pero más que el tope de WebP.
    - `test_formato_no_permitido_se_rechaza`: un ICNS generado con Pillow, más GIF y BMP en `subTest`.
  - `test_exif_corrupto_no_impide_guardar` sigue en verde, porque el mock de `exif_transpose` acepta el kwarg `in_place`.
  - **Agregado por la auditoría de seguridad** (modificación del contrato decidida por el usuario):
    - MPO: Pillow abre las fotos MPO por el plugin JPEG, pero `original.format == "MPO"`, y eso daba un `KeyError` y un 500. Agregar `"MPO"` con el tope de JPEG y buscar el tope con `.get()`: un formato sin tope se rechaza con `ValidationError`, no explota. Test `test_mpo_se_acepta`: un MPO de dos cuadros generado con Pillow (`save_all=True`) se guarda como JPEG de un solo cuadro.
    - `ValueError`: un `zTXt` o `iTXt` que descomprime más de `MAX_TEXT_CHUNK` lanza `ValueError` en `open` o en `load`. Agregar `ValueError` al `except` externo, con un comentario. Test `test_png_con_ztxt_enorme_se_rechaza`: un PNG chico con un `zTXt` de más de 1 MB descomprimido, ubicado después del IDAT, lanza `ValidationError`.
    - Memoria:
      - WebP baja a 8 MP.
      - Un JPEG o MPO progresivo (`original.info.get("progressive")`) o CMYK usa `MAX_PIXELES_JPEG_COSTOSO = 16_000_000`, porque libjpeg guarda los coeficientes a resolución completa y `draft` no lo reduce.
      - Test `test_webp_de_10_mp_se_rechaza`: un WebP de 4000×2500 lanza `ValidationError`.
      - Test `test_jpeg_progresivo_grande_se_rechaza`: un JPEG progresivo de 5000×4000 (20 MP) lanza `ValidationError`, y el mismo tamaño en baseline se acepta.
    - El presupuesto sigue en 160.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_fotos.FotoTests.test_png_corrupto_se_rechaza --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_fotos.FotoTests.test_webp_con_dimensiones_enormes_se_rechaza --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_fotos.FotoTests.test_formato_no_permitido_se_rechaza --keepdb`
  - `[grep-1]` `grep -n 'formats=("JPEG", "PNG", "WEBP")' apps/visitas/imagenes.py`
  - `[grep-1]` `grep -n "in_place=True" apps/visitas/imagenes.py`
  - `[grep-1]` `grep -n "MAX_PIXELES_POR_FORMATO" apps/visitas/imagenes.py`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_fotos.FotoTests.test_mpo_se_acepta --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_fotos.FotoTests.test_png_con_ztxt_enorme_se_rechaza --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_fotos.FotoTests.test_webp_de_10_mp_se_rechaza --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_fotos.FotoTests.test_jpeg_progresivo_grande_se_rechaza --keepdb`
  - `[grep-1]` `grep -n "MAX_PIXELES_JPEG_COSTOSO" apps/visitas/imagenes.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check apps/visitas`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-03-menores-abiertos.md menores-abiertos)" 160 apps/visitas/imagenes.py apps/visitas/tests/test_fotos.py`

### T2 — Error de formulario para fotos inválidas y planificación de solo lectura en visitas cerradas

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/visitas/admin.py`, `apps/visitas/tests/test_admin.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/visitas/models.py`, `apps/visitas/imagenes.py`, `apps/visitas/services.py`, `apps/visitas/migrations/`, `apps/visitas/tests/test_fotos.py`, `apps/visitas/tests/test_models.py`, `apps/visitas/tests/test_services.py`, cualquier otra app
- **Skill a leer antes**: `.agents/skills/django-security/SKILL.md` § File Upload Security y § Authorization
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 200 líneas agregadas
- **Qué hacer**:
  - **N4**: crear `FotoInlineForm(forms.ModelForm)` con `clean_imagen`.
    - Si el valor es un `UploadedFile` nuevo, llama a `imagenes.procesar_imagen(archivo)` y descarta el resultado: la `ValidationError` queda como error del campo.
    - Después hace `archivo.seek(0)` y devuelve el archivo.
    - Un `FieldFile` ya guardado no se procesa.
    - `FotoInline.form = FotoInlineForm` y `FotoAdmin.form = FotoInlineForm`. `FotoAdmin` permite cambiar `imagen` en una foto de visita pendiente, y ese camino también daba 500.
  - **N5**: en una visita no pendiente, `get_readonly_fields` agrega `programada_para` y `asignada_por`, en una tupla aparte o sumada a la de evidencia. `observaciones`, `incidencia` e `incidencia_detalle` siguen editables.
  - `test_imagen_invalida_da_error_de_formulario_no_500`, que falla antes del cambio:
    1. como superusuario, hace POST al change de una visita **pendiente**, con los datos del formulario y los management forms de los dos inlines;
    2. el POST lleva una foto nueva: un PNG de 8000×6000 que pasa `forms.ImageField` pero que `procesar_imagen` rechaza;
    3. espera 200, un error en el formset de fotos y `Foto.objects.count() == 0`.
  - `test_foto_admin_imagen_invalida_da_error_de_formulario`, que falla antes del cambio:
    1. como superusuario, hace POST al change de `FotoAdmin` de una foto de visita pendiente, con el mismo PNG de 8000×6000 y los demás campos;
    2. espera 200, un error en el campo `imagen` y que `foto.imagen.name` no cambie.
  - `test_programada_para_solo_lectura_en_realizada`, que falla antes del cambio:
    - para una visita realizada, `programada_para` y `asignada_por` están en `get_readonly_fields`, y `observaciones`, `incidencia` e `incidencia_detalle` no;
    - para una pendiente, `programada_para` y `asignada_por` no están.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_admin.VisitaAdminTests.test_programada_para_solo_lectura_en_realizada --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_admin.VisitaAdminTests.test_imagen_invalida_da_error_de_formulario_no_500 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_admin.VisitaAdminTests.test_foto_admin_imagen_invalida_da_error_de_formulario --keepdb`
  - `[grep-1]` `grep -n "def clean_imagen" apps/visitas/admin.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check apps/visitas`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-03-menores-abiertos.md menores-abiertos)" 200 apps/visitas/admin.py apps/visitas/tests/test_admin.py`

### T3 — Validar argumentos de los scripts de worktree y deshacer el merge si fallan los tests

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `.claude/hooks/worktree-integrar.sh`, `.claude/hooks/worktree-crear.sh`, `.claude/hooks/test_worktree.py`
- **No puede tocar**: `docs/planes/`, `.claude/hooks/verificar_plan.py`, `.claude/hooks/test_verificar_plan.py`, `.claude/hooks/congelado.sh`, `.claude/hooks/presupuesto.sh`, `.claude/hooks/cambios.sh`, `.claude/hooks/contexto.sh`, `apps/`, `config/`, `venv/`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § Worktrees
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 220 líneas agregadas
- **Qué hacer**:
  - `worktree-integrar.sh`:
    - Rechaza con exit 2 cualquier `<ruta>` vacía. Quita la `/` final de cada prefijo.
    - El alcance compara por segmento: `"$p"|"$p"/*`.
    - Antes de tocar nada, comprueba que `worktrees/<slug>-T<n>` figura en `git worktree list --porcelain`, normalizando la ruta. Si no figura, exit 1.
    - Si `makemigrations --check` o `test` fallan después del merge, ejecuta `git -C "$ruta_dest" reset --hard ORIG_HEAD` (el destino estaba limpio por el paso 1) y escribe en stderr `se deshizo el merge de <nombre> en <destino>`. Sale con 1 y deja el worktree y la rama intactos. Actualizar el encabezado del script.
  - `worktree-crear.sh`: rechaza con exit 2 un `rama_base` que empiece con `-` o que no resuelva con `git rev-parse --verify --quiet "<rama_base>^{commit}"`, antes de `worktree add`.
  - Tests nuevos en `test_worktree.py`, con el fixture `repo` existente. Todos fallan antes del cambio:
    - `test_integrar_rechaza_prefijo_vacio`: con `""` entre las rutas, sale distinto de 0 y `main` no cambia.
    - `test_integrar_compara_por_segmento`: commitea `app/x.txt` y `app_v2/y.txt` e integra con `app`. Se rechaza, stderr nombra `app_v2/y.txt` y `main` no cambia.
    - `test_integrar_deshace_merge_si_fallan_tests`: la raíz tiene un `manage.py` de juguete que sale con 1 cuando recibe `test`. Al integrar sale con 1, `main` vuelve al hash anterior, stderr contiene `se deshizo el merge`, y el worktree y la rama siguen.
    - `test_integrar_rechaza_ruta_que_no_es_worktree`:
      - preparación: la rama `demo-T1` tiene un commit propio, `app.txt`, y `worktrees/demo-T1` es un directorio común, no registrado;
      - al integrar con la ruta `app.txt`, sale con 1 y el hash de `main` es el mismo antes y después;
      - el commit propio es lo que hace que el script actual mergee y que el test falle antes del cambio.
    - `test_crear_rechaza_rama_base_invalida`: tres `subTest` o parametrizaciones, con `-b`, `--orphan` y `no-existe`. Sale con 2, no existe `worktrees/demo-T1` ni la rama `demo-T1`.
- **Criterios**:
  - `[test]` `py -3 -m pytest .claude/hooks/test_worktree.py::test_integrar_rechaza_prefijo_vacio -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_worktree.py::test_integrar_compara_por_segmento -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_worktree.py::test_integrar_deshace_merge_si_fallan_tests -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_worktree.py::test_integrar_rechaza_ruta_que_no_es_worktree -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_worktree.py::test_crear_rechaza_rama_base_invalida -q`
  - `[grep-1]` `grep -n "reset --hard ORIG_HEAD" .claude/hooks/worktree-integrar.sh`
  - `[grep-1]` `grep -n "worktree list --porcelain" .claude/hooks/worktree-integrar.sh`
  - `[cmd]` `py -3 -m pytest .claude/hooks/test_worktree.py -q`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-03-menores-abiertos.md menores-abiertos)" 220 .claude/hooks/worktree-integrar.sh .claude/hooks/worktree-crear.sh .claude/hooks/test_worktree.py`

### T4 — Plantilla de plan: integración por ola sin criterios que nadie ejecuta

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `docs/plantilla-plan.md`, `.claude/hooks/test_verificar_plan.py`
- **No puede tocar**: `docs/planes/`, `CLAUDE.md`, `.claude/hooks/verificar_plan.py`, `.claude/hooks/worktree-integrar.sh`, `.claude/hooks/worktree-crear.sh`, `.claude/hooks/test_worktree.py`, `.claude/agents/`, `apps/`, `config/`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § Olas por grafo de FK
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 100 líneas agregadas
- **Qué hacer**:
  - Quitar `## Trabajo del principal (integración)` con sus `### Ola 1` y `### Ola 2`.
  - Dentro de `## Subtareas`, cada ola termina con un encabezado `### Trabajo del principal (integración de la ola N)`: T1 y T2, integración de la ola 1, T3, integración de la ola 2. Tiene que ser un encabezado y no un párrafo en negrita: el hook corta la tarea en cualquier encabezado, y sin él los criterios se sumarían a la última `T<n>`.
  - Cada bloque lista los pasos (`worktree-crear.sh`, `cambios.sh`, `worktree-integrar.sh`, cableado y migraciones) y lleva su `- **Criterios**:` con criterios concretos.
    - Ola 1: `` `[cmd]` `git log --oneline plan/<slug> | grep -q "T1: integra <slug>-T1"` ``.
    - Ola 2: el mismo criterio, con `T3`.
  - Agregar una nota en un comentario: `verificar_plan.py` y `verificador` solo ejecutan `### T<n>` y `## Criterios de cierre global`. Los criterios de integración los corre el principal antes de abrir la ola siguiente y pega la salida en `### Corridas`; lo que deba quedar comprobado al cierre se repite en el cierre global.
  - Test nuevo `test_plantilla_integracion_de_ola_fuera_de_las_tareas` en `test_verificar_plan.py`:
    - parsea `docs/plantilla-plan.md` con `parsear_plan` y falla con la plantilla actual;
    - (a) la línea `T1: integra <slug>-T1` está en el texto, después del encabezado `### Trabajo del principal (integración de la ola 1)`;
    - (b) esa línea no está en ningún `criterios[n]`;
    - (c) `3 in criterios`: `### T3` existe, el layout nuevo;
    - (d) el cierre global sigue con 6 criterios.
- **Criterios**:
  - `[test]` `py -3 -m pytest .claude/hooks/test_verificar_plan.py::test_plantilla_integracion_de_ola_fuera_de_las_tareas -q`
  - `[grep-0]` `grep -n "^### Ola " docs/plantilla-plan.md`
  - `[grep-1]` `grep -n "^### Trabajo del principal (integración de la ola 1)" docs/plantilla-plan.md`
  - `[grep-1]` `grep -n "^### Trabajo del principal (integración de la ola 2)" docs/plantilla-plan.md`
  - `[grep-1]` `grep -n "solo ejecutan" docs/plantilla-plan.md`
  - `[cmd]` `py -3 -m pytest .claude/hooks/test_verificar_plan.py -q`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-03-menores-abiertos.md menores-abiertos)" 100 docs/plantilla-plan.md .claude/hooks/test_verificar_plan.py`

### Trabajo del principal (integración de la ola 1)

1. Crear los worktrees con `bash .claude/hooks/worktree-crear.sh menores-abiertos T<n> plan/menores-abiertos`, para T1 a T4.
2. Por cada subtarea, revisar `bash .claude/hooks/cambios.sh worktrees/menores-abiertos-T<n> plan/menores-abiertos`.
3. Integrar con `bash .claude/hooks/worktree-integrar.sh menores-abiertos T<n> plan/menores-abiertos <rutas de Puede tocar>`.

T3 cambia `worktree-integrar.sh`: se integra con el script de `plan/menores-abiertos` tal como esté en ese momento. Los criterios de integración van en el cierre global, porque el hook no ejecuta este bloque.

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `py -3 -m pytest .claude/hooks -q`
- `[cmd]` `git log --oneline plan/menores-abiertos | grep -q "T1: integra menores-abiertos-T1"`
- `[cmd]` `git log --oneline plan/menores-abiertos | grep -q "T2: integra menores-abiertos-T2"`
- `[cmd]` `git log --oneline plan/menores-abiertos | grep -q "T3: integra menores-abiertos-T3"`
- `[cmd]` `git log --oneline plan/menores-abiertos | grep -q "T4: integra menores-abiertos-T4"`
- `[cmd-falla]` `git worktree list | grep -q "menores-abiertos-T"`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-03-menores-abiertos.md menores-abiertos`

## Registro de verificación

commit_base: b437ec1

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | en curso |
| T2 | en curso |
| T3 | en curso |
| T4 | en curso |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| | T1 | | | |
| | T2 | | | |
| | T3 | | | |
| | T4 | | | |
| | TODO | | | |

## Al cerrar (principal)

En `docs/bitacora.md`:
- marcar cerrados los menores resueltos;
- dejar abiertas la junction tras la prueba de humo fallida y las observaciones de T1.

En `docs/decisiones.md`, agregar:
- el tope por formato y la lista de formatos permitidos;
- N5: la planificación es de solo lectura en una visita cerrada; las observaciones y la incidencia siguen editables;
- la integración por ola va en encabezados propios fuera de las tareas.
