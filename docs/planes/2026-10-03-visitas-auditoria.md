# Plan: corregir los hallazgos de la auditoría de visitas

- **slug**: `visitas-auditoria`
- **fecha**: 2026-10-03
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): visitas-auditoria`. El hash se anota en `## Registro de verificación`.
- **objetivo**: la evidencia de una visita realizada no se puede alterar ni borrar desde el admin; el registro de visitas resiste reintentos, visitas atrasadas e imágenes maliciosas; y las fotos borradas no quedan en disco.
- **fuera de alcance** (quedan abiertos en la bitácora):
  - el original que pasa por el temporal del sistema (menor 8) y HEIC (menor 10);
  - empleado distinto del asignado (menor 12, va con el plan de API);
  - retención de `HistoricalVisita` y de visitas al suprimir un sitio (menor 13 y decisión legal del 6);
  - servir MEDIA (menor 14);
  - los bloques `### Ola` de la plantilla.
- **áreas**: dominio (modelos y servicios)
- **seguridad**: sí. Toca la subida de fotos, las coordenadas, el historial (datos personales) y el borrado de archivos. Por eso corre también `auditor-seguridad`, para verificar las correcciones.

## Contexto mínimo

- Plan de origen: `docs/planes/2026-10-03-visitas.md` (TODO PASA 60/60). Los hallazgos están en `docs/bitacora.md`, en "Auditoría de `visitas`".
- Rama: `plan/visitas-auditoria`, que sale de `plan/visitas` (`d7cd815`). Al cerrar con TODO PASA, `main` avanza por fast-forward hasta esa rama, con los dos planes.
- Archivos:
  - `apps/visitas/imagenes.py`: `procesar_imagen`;
  - `apps/visitas/models.py`: `Foto.save` y `ProductoAplicado`, que no tiene historial;
  - `apps/visitas/services.py`: `registrar_visita_realizada` valida sobre la instancia recibida, sin bloqueo;
  - `apps/visitas/admin.py`: solo `estado`, `realizada_en` y `esquema_planilla` son de solo lectura.
- Corrección por hallazgo:

| Hallazgo | Corrección | Subtarea |
|---|---|---|
| 1. Bomba de descompresión | Tope de píxeles y decodificación reducida | T1 |
| 7. Comentario JPEG/GIF que sobrevive | Se descartan los metadatos de `info` | T1 |
| 9. Archivo que no es imagen da 500 | Se relanza como `ValidationError` | T1 |
| 3 (parte de modelo). Productos sin historial | Historial en `ProductoAplicado` | T2 |
| 6 (parte de archivos). JPEG que queda en disco | Borrado del archivo al borrar o reemplazar la foto | T2 |
| 4 y 11. Doble registro y visita mutada en memoria | Bloqueo y relectura | T3 |
| 5. Visita atrasada que retrocede el proyecto | Solo actualiza el proyecto la visita más reciente | T3 |
| 2, 3 y 6 (parte de admin). Evidencia editable y borrable | Solo lectura y sin borrado | T4 |

- Decisiones:
  - `registrar_visita_realizada` relee la visita y el proyecto con `select_for_update` dentro del `atomic`, valida sobre la copia releída y la devuelve. La instancia que recibe ya no se modifica, así que la visita tiene que estar guardada.
  - Tolerancia para fechas futuras: `TOLERANCIA_FUTURO = timedelta(minutes=10)`.
  - `ProductoAplicado` pasa a tener historial: `docs/01-modelo-y-arquitectura.md:170` dice "Proyecto, Sitio y Visita". Lote y dosis son datos regulatorios del certificado. Se anota en `docs/decisiones.md` en el commit `registro:` del commit_base.
  - Desde el admin no se borran visitas ni fotos (coherente con "borrado de visitas fuera de alcance"). Con la visita no pendiente, fotos y productos son de solo lectura.

## Olas

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1, T2, T3, T4 | visitas (`0002`, solo T2). Las cuatro tocan archivos disjuntos de `apps/visitas`. |

## Subtareas

### T1 — Blindar procesar_imagen contra bombas, metadatos residuales y archivos que no son imagen

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/visitas/imagenes.py`, `apps/visitas/tests/test_fotos.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/visitas/models.py`, `apps/visitas/services.py`, `apps/visitas/admin.py`, `apps/visitas/migrations/`, `apps/visitas/tests/test_models.py`, `apps/visitas/tests/test_services.py`, `apps/visitas/tests/test_admin.py`, cualquier otra app
- **Skill a leer antes**: `.agents/skills/django-security/SKILL.md` § File Upload Security
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 250 líneas agregadas
- **Qué hacer**:
  - Constante `MAX_PIXELES = 40_000_000`. Si `ancho * alto` supera ese valor, se lanza `ValidationError` antes de decodificar.
  - Llamar a `original.draft("RGB", (LADO_MAXIMO, LADO_MAXIMO))` antes de `exif_transpose`.
  - Dentro de `warnings.catch_warnings()`, convertir `Image.DecompressionBombWarning` en error.
  - Capturar `UnidentifiedImageError`, `OSError`, `Image.DecompressionBombError` y `Image.DecompressionBombWarning`, y relanzarlas como `ValidationError("El archivo no es una imagen válida.")`.
  - Antes de guardar, `imagen.info = {}`, para que no sobreviva el comentario.
  - Los tests fallan antes del cambio:
    - un PNG en escala de grises de 8000×6000 (48 Mpx) da `ValidationError` y no crea ninguna `Foto`;
    - un JPEG con `comment=b"SECRETO"` no deja `SECRETO` en los bytes guardados;
    - bytes que no son imagen dan `ValidationError`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_fotos.FotoTests.test_rechaza_imagen_con_demasiados_pixeles --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_fotos.FotoTests.test_quita_comentario_del_jpeg --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_fotos.FotoTests.test_archivo_que_no_es_imagen_lanza_validation_error --keepdb`
  - `[grep-1]` `grep -n "MAX_PIXELES = 40_000_000" apps/visitas/imagenes.py`
  - `[grep-1]` `grep -n "draft(" apps/visitas/imagenes.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check apps/visitas`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-03-visitas-auditoria.md visitas-auditoria)" 250 apps/visitas/imagenes.py apps/visitas/tests/test_fotos.py`

### T2 — Historial de productos aplicados y borrado de archivos de fotos

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/visitas/models.py`, `apps/visitas/migrations/`, `apps/visitas/tests/test_models.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/visitas/imagenes.py`, `apps/visitas/services.py`, `apps/visitas/admin.py`, `apps/visitas/tests/test_fotos.py`, `apps/visitas/tests/test_services.py`, `apps/visitas/tests/test_admin.py`, cualquier otra app, migraciones existentes
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Task 2: Model Best Practices
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 250 líneas agregadas en `models.py` y `tests/test_models.py`. No se cuenta la migración autogenerada.
- **Qué hacer**:
  - `ProductoAplicado.history = HistoricalRecords()`, y `makemigrations visitas` sin edición a mano.
  - Un receptor `post_delete` de `Foto`, en `models.py`, que borre el archivo con `transaction.on_commit(lambda: storage.delete(nombre))`.
  - En `Foto.save`, si la foto ya existía y cambió el archivo, borrar el anterior en `on_commit`.
  - No modificar el helper `crear_visita` ni las clases existentes de `test_models.py`: lo importan `test_fotos.py` (T1) y `test_services.py` (T3). Solo se agregan clases nuevas.
  - Los tests usan `override_settings(MEDIA_ROOT=<tempdir>)`, `self.captureOnCommitCallbacks(execute=True)` e imágenes reales de Pillow. Comprueban:
    - el archivo desaparece al borrar la foto, también al borrar la visita en cascada;
    - al reemplazar la imagen se borra el archivo anterior;
    - el historial de producto aplicado registra un cambio de `lote`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_models.FotoArchivoTests.test_borrar_foto_borra_el_archivo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_models.FotoArchivoTests.test_borrar_visita_borra_los_archivos_de_sus_fotos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_models.FotoArchivoTests.test_reemplazar_imagen_borra_el_archivo_anterior --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_models.ProductoAplicadoTests.test_historial_registra_cambio_de_lote --keepdb`
  - `[existe]` `apps/visitas/migrations/0002_historicalproductoaplicado.py`
  - `[grep-1]` `grep -n "post_delete" apps/visitas/models.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check apps/visitas`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-03-visitas-auditoria.md visitas-auditoria)" 250 apps/visitas/models.py apps/visitas/tests/test_models.py`

### T3 — Registro de visita con bloqueo, sin retroceder el proyecto y sin fechas futuras

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/visitas/services.py`, `apps/visitas/tests/test_services.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/visitas/models.py`, `apps/visitas/imagenes.py`, `apps/visitas/admin.py`, `apps/visitas/migrations/`, `apps/visitas/tests/test_models.py`, `apps/visitas/tests/test_fotos.py`, `apps/visitas/tests/test_admin.py`, cualquier otra app
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Task 2 (servicios y transacciones) y § Task 8: Testing
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 300 líneas agregadas
- **Qué hacer**:
  - Todo el cuerpo va dentro de `transaction.atomic()`:
    - releer con `Visita.objects.select_for_update().get(pk=visita.pk)` y `Proyecto.objects.select_for_update().get(pk=...)`;
    - las validaciones existentes corren sobre la copia releída;
    - agregar la validación `realizada_en > timezone.now() + TOLERANCIA_FUTURO`, que lanza `ValidationError`;
    - guardar la visita;
    - actualizar `encargado_actual`/`proxima_visita` solo si ninguna otra visita realizada del proyecto tiene `realizada_en` posterior.
  - Devuelve la copia releída; la instancia recibida no se modifica (resuelve el menor 11).
  - Hoy los tests usan `self.ahora = 2026-10-03 12:00`, que puede quedar en el futuro según la hora en que corran. Pasarlo a una fecha pasada fija y ajustar las fechas esperadas, sin debilitar ningún test existente ni cambiarle el nombre.
  - Tests nuevos, que fallan antes del cambio:
    - dos instancias leídas por separado del mismo pk, ambas antes del primer registro (como dos requests concurrentes): la segunda llamada da `ValidationError` y no pisa ni `empleado` ni `realizada_en` de la primera. Hoy registra dos veces;
    - una visita con `realizada_en` anterior a la última realizada no cambia `encargado_actual` ni `proxima_visita`;
    - `realizada_en` una hora en el futuro da `ValidationError`;
    - cuando `full_clean` falla (empleado administrador), la instancia recibida sigue en `pendiente`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.RegistrarVisitaTests.test_doble_registro_con_lecturas_distintas_falla --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.RegistrarVisitaTests.test_visita_atrasada_no_retrocede_el_proyecto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.RegistrarVisitaTests.test_rechaza_realizada_en_futura --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_services.RegistrarVisitaTests.test_falla_de_validacion_no_muta_la_instancia --keepdb`
  - `[grep-1]` `grep -n "select_for_update" apps/visitas/services.py`
  - `[grep-1]` `grep -n "TOLERANCIA_FUTURO = timedelta(minutes=10)" apps/visitas/services.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check apps/visitas`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-03-visitas-auditoria.md visitas-auditoria)" 300 apps/visitas/services.py apps/visitas/tests/test_services.py`

### T4 — Admin: evidencia de solo lectura y sin borrado de visitas ni fotos

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/visitas/admin.py`, `apps/visitas/tests/test_admin.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/visitas/models.py`, `apps/visitas/imagenes.py`, `apps/visitas/services.py`, `apps/visitas/migrations/`, `apps/visitas/tests/test_models.py`, `apps/visitas/tests/test_fotos.py`, `apps/visitas/tests/test_services.py`, cualquier otra app
- **Skill a leer antes**: `.agents/skills/django-security/SKILL.md` § Authorization; `.claude/skills/convenciones-proyecto/SKILL.md` § prohibiciones (sin reglas de negocio en `admin.py`: solo permisos y solo lectura)
- **Worktree**: sí
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 250 líneas agregadas
- **Qué hacer**:
  - **Campos de evidencia**:
    - `CAMPOS_EVIDENCIA = ("proyecto", "empleado", "origen", "motivo_manual", "latitud", "longitud", "precision_m", "datos", "estado", "realizada_en", "esquema_planilla")`.
    - `VisitaAdmin.get_readonly_fields` los devuelve todos cuando `obj` existe y su `estado` no es `pendiente`.
  - **Borrado**: `has_delete_permission` siempre en `False` en `VisitaAdmin`, `FotoInline` y `FotoAdmin`.
  - **Inlines**: `FotoInline` y `ProductoAplicadoInline` devuelven `False` en `has_add_permission`/`has_change_permission`/`has_delete_permission` cuando la visita padre no está pendiente.
  - **Admins sueltos**:
    - `FotoAdmin` y `ProductoAplicadoAdmin`: `has_add_permission` en `False`.
    - `has_change_permission` en `False` si `obj.visita` no está pendiente.
    - `ProductoAplicadoAdmin.has_delete_permission`: igual que `has_change_permission`.
  - **Tests**, que fallan antes del cambio:
    - los campos de evidencia son de solo lectura en una visita realizada y editables en una pendiente;
    - un superusuario no puede borrar visitas ni fotos: el POST de borrado da 403 y la fila sigue;
    - los inlines no permiten agregar, cambiar ni borrar en una visita realizada;
    - `FotoAdmin` no permite cambiar una foto de una visita realizada.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_admin.VisitaAdminTests.test_visita_realizada_tiene_evidencia_de_solo_lectura --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_admin.VisitaAdminTests.test_no_se_borran_visitas_ni_fotos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_admin.VisitaAdminTests.test_inlines_bloqueados_en_visita_realizada --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_admin.VisitaAdminTests.test_foto_admin_no_cambia_foto_de_visita_realizada --keepdb`
  - `[grep-1]` `grep -n "CAMPOS_EVIDENCIA" apps/visitas/admin.py`
  - `[grep-1]` `grep -n "def has_delete_permission" apps/visitas/admin.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check apps/visitas`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-03-visitas-auditoria.md visitas-auditoria)" 250 apps/visitas/admin.py apps/visitas/tests/test_admin.py`

## Trabajo del principal (integración)

Una sola ola:
1. Crear los cuatro worktrees con `bash .claude/hooks/worktree-crear.sh visitas-auditoria T<n> plan/visitas-auditoria`.
2. Revisar `cambios.sh` e integrar cada uno con `worktree-integrar.sh` usando sus rutas de `Puede tocar`.
3. Correr la verificación final y la re-auditoría.
4. Hacer el fast-forward de `main` a `plan/visitas-auditoria`. Los criterios de integración van en el cierre global, porque nada ejecuta los bloques `### Ola`.

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[grep-0]` `grep -rn "fields = \"__all__\"" apps/`
- `[cmd]` `git log --oneline plan/visitas-auditoria | grep -q "T1: integra visitas-auditoria-T1"`
- `[cmd]` `git log --oneline plan/visitas-auditoria | grep -q "T2: integra visitas-auditoria-T2"`
- `[cmd]` `git log --oneline plan/visitas-auditoria | grep -q "T3: integra visitas-auditoria-T3"`
- `[cmd]` `git log --oneline plan/visitas-auditoria | grep -q "T4: integra visitas-auditoria-T4"`
- `[cmd-falla]` `git worktree list | grep -q "visitas-auditoria-T"`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-03-visitas-auditoria.md visitas-auditoria`

## Registro de verificación

commit_base: <hash del commit docs(plan): visitas-auditoria>

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
| | T1 | | | |
| | TODO | | | |
