# Plan: Modelos de dominio (clientes, sitios, servicios, proyectos, productos)

- **slug**: `modelos-dominio`
- **fecha**: 2026-10-02
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): modelos-dominio`. No se escribe acá: el hash se anota en `## Registro de verificación`.
- **objetivo**: los administradores pueden cargar clientes, sitios (con su QR), tipos de servicio con su planilla, proyectos y productos desde el admin técnico, con historial de cambios en sitios y proyectos.
- **fuera de alcance**: Visita, Foto, ProductoAplicado, Certificado; vistas, API, panel, serializers; cambios en `apps/accounts`; generación de la imagen del QR; `ultima_visita` (depende de Visita); campos de planilla en el fixture.
- **áreas**: dominio (modelos y servicios) | infraestructura (`INSTALLED_APPS`, `MIDDLEWARE`)
- **seguridad**: sí — QR (`Sitio.qr_codigo`), geolocalización (`latitud`/`longitud`), datos personales de contacto de clientes y sitios, FK a usuarios con filtro de rol. Corre `auditor-seguridad` al cierre.

## Contexto mínimo

- Las apps `apps/{clientes,sitios,servicios,proyectos,productos}` son esqueletos: `models.py` tiene solo un docstring, hay `tests/__init__.py` y no hay `admin.py` ni `migrations/`.
- La especificación está en `docs/01-modelo-y-arquitectura.md` §3.1 (Cliente), §3.2 (Sitio), §3.3 (TipoServicio), §3.4 (CampoPlanilla), §3.5 (Proyecto), §3.9 (Producto) y §6 (simple_history en Sitio y Proyecto).
- Patrón a seguir: `apps/accounts/models.py` (docstring en español, `TextChoices` anidado, verbose_name posicional, `Meta` con verbose_name en minúscula) y `apps/accounts/tests/test_user.py` (`TestCase`, imports absolutos).
- Los encargados se filtran con `limit_choices_to={"rol": "empleado"}`, que es el valor de `User.Rol.EMPLEADO`. `full_clean()` también aplica el filtro (`ForeignKey.validate`), y eso es lo que fija el test.
- `estado_visita` se calcula solo con `proxima_visita` contra `timezone.localdate()`:
  - `None` → `sin_programar`;
  - `< hoy` → `vencida`;
  - `<= hoy + 7 días` → `proxima`;
  - en otro caso → `al_dia`.
- `on_delete`: `PROTECT` en Sitio.cliente, Proyecto.sitio, Proyecto.tipo_servicio y en los dos encargados; `CASCADE` en CampoPlanilla.tipo_servicio.
- El campo `activo` de los modelos de dominio es un `BooleanField(default=True)` propio. La decisión 2026-10-01 (`is_active`) aplica solo a User.
- El fixture lleva 9 servicios (decisión 2026-10-02): los 8 títulos de `docs/00-contenido-fuente.md` §Servicios más "Mantenimiento edilicio", con `pk` explícito para que `loaddata` sea idempotente.
- Las subtareas corren en dos olas:
  - Ola 1, en paralelo, cada una en su worktree con una junction a `venv/`: T1 (clientes + sitios), T2 (servicios), T3 (productos). Sitios va con clientes porque su migración depende de la de clientes.
  - Ola 2, sobre `main` integrado: T4 (proyectos), cuya migración depende de sitios y servicios.
  - Una subtarea de la ola 1 queda `hecha` recién después del merge, porque el hook corre los criterios desde la raíz.

## Subtareas

### T1 — Crear Cliente y Sitio con QR e historial, y activar simple_history

- **Depende de**: —
- **Puede tocar**: `apps/clientes/models.py`, `apps/clientes/admin.py`, `apps/clientes/migrations/`, `apps/clientes/tests/test_models.py`, `apps/sitios/models.py`, `apps/sitios/admin.py`, `apps/sitios/migrations/`, `apps/sitios/tests/test_models.py`, `config/settings/base.py`
- **No puede tocar**: `docs/planes/`, `apps/accounts/`, `apps/servicios/`, `apps/productos/`, `apps/proyectos/`, migraciones existentes de otras apps
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Task 2: Model Best Practices; `.claude/skills/convenciones-proyecto/SKILL.md` § prohibiciones
- **Worktree**: sí (`worktrees/modelos-dominio-T1`)
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 550 líneas agregadas (incluye migraciones autogeneradas, y la de Sitio duplica la tabla por el historial)
- **Qué hacer**:
  - `config/settings/base.py`: agregar `"simple_history",` a `INSTALLED_APPS` y `"simple_history.middleware.HistoryRequestMiddleware",` al final de `MIDDLEWARE`.
  - Cliente según §3.1: `cuit` opcional con `RegexValidator(r"^\d{11}$")`, más `contacto_nombre`, `contacto_telefono`, `contacto_email`, `notas`, `activo`, `creado` y `actualizado`.
  - Sitio según §3.2:
    - `sector` con choices de §3.2: valor sin tilde, etiqueta con tilde;
    - `latitud` y `longitud` como `DecimalField(9, 6)` con `null=True, blank=True`;
    - `qr_codigo = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)`;
    - `qr_impreso_el`;
    - `history = HistoricalRecords()`.
  - `__str__` en los dos modelos. Admin con `list_display` y `search_fields`; Sitio con `SimpleHistoryAdmin`.
  - Migraciones generadas con `makemigrations`, sin editarlas a mano.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.clientes.tests.test_models.ClienteTests.test_cuit_invalido_no_valida --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.clientes.tests.test_models.ClienteTests.test_cuit_es_opcional --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_models.SitioTests.test_qr_codigo_se_genera_y_es_unico --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_models.SitioTests.test_qr_codigo_no_es_editable --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_models.SitioTests.test_historial_registra_cambios --keepdb`
  - `[grep-1]` `grep -n '"simple_history",' config/settings/base.py`
  - `[grep-1]` `grep -n "simple_history.middleware.HistoryRequestMiddleware" config/settings/base.py`
  - `[grep-1]` `grep -n "qr_codigo = models.UUIDField" apps/sitios/models.py`
  - `[grep-1]` `grep -n "SimpleHistoryAdmin" apps/sitios/admin.py`
  - `[grep-1]` `grep -n "search_fields" apps/clientes/admin.py`
  - `[existe]` `apps/clientes/migrations/0001_initial.py`
  - `[existe]` `apps/sitios/migrations/0001_initial.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check apps/clientes apps/sitios config`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-02-modelos-dominio.md modelos-dominio)" 550 apps/clientes apps/sitios config/settings/base.py`

### T2 — Crear TipoServicio, CampoPlanilla y el fixture de servicios

- **Depende de**: —
- **Puede tocar**: `apps/servicios/models.py`, `apps/servicios/admin.py`, `apps/servicios/migrations/`, `apps/servicios/fixtures/tipos_servicio.json`, `apps/servicios/tests/test_models.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/accounts/`, `apps/clientes/`, `apps/sitios/`, `apps/productos/`, `apps/proyectos/`, migraciones existentes de otras apps
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Task 2: Model Best Practices; `.claude/skills/convenciones-proyecto/SKILL.md` § prohibiciones
- **Worktree**: sí (`worktrees/modelos-dominio-T2`)
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 400 líneas agregadas (incluye la migración autogenerada y el fixture)
- **Qué hacer**:
  - TipoServicio: `nombre`, `slug` (`SlugField(unique=True)`), `descripcion`, `activo`. El método `esquema_planilla()` devuelve `list[dict]` con `clave`, `etiqueta`, `tipo`, `opciones`, `obligatorio`, `ayuda` y `orden`, ordenada por `orden`.
  - CampoPlanilla según §3.4: `tipo` con choices `texto`, `numero`, `booleano`, `opcion`, `opcion_multiple`, `fecha`; `opciones = JSONField(default=list, blank=True)`; `clave` como `SlugField`; `UniqueConstraint(fields=["tipo_servicio", "clave"])`; `ordering = ["orden"]`.
  - El fixture `apps/servicios/fixtures/tipos_servicio.json` lleva 9 objetos con `pk` 1 a 9 y sin campos de planilla. Los nombres son literales de `docs/00-contenido-fuente.md`:
    1. Desinfección, sanitización y desodorización
    2. Control de plagas urbanas
    3. Servicio MIPU (Manejo Integral de Plagas Urbanas)
    4. Mosquitos vectores — erradicación y prevención
    5. Control de murciélagos
    6. Exclusión de palomas y otras aves
    7. Limpieza y desinfección de tanques de agua y cisternas
    8. Manejo integral de plagas en edificios / departamentos
    9. Mantenimiento edilicio
  - Las descripciones del fixture se toman de ese mismo archivo, recortadas a la primera oración y sin inventar texto.
  - Admin con `list_display` y `search_fields`. CampoPlanilla va como inline tabular de TipoServicio.
  - El test del fixture usa `fixtures = ["tipos_servicio"]` y comprueba que haya 9 registros.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.servicios.tests.test_models.CampoPlanillaTests.test_clave_unica_por_tipo_servicio --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.servicios.tests.test_models.CampoPlanillaTests.test_misma_clave_en_otro_tipo_servicio_es_valida --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.servicios.tests.test_models.TipoServicioTests.test_esquema_planilla_respeta_orden --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.servicios.tests.test_models.TipoServicioTests.test_fixture_carga_nueve_servicios --keepdb`
  - `[existe]` `apps/servicios/fixtures/tipos_servicio.json`
  - `[existe]` `apps/servicios/migrations/0001_initial.py`
  - `[grep-1]` `grep -n "Mantenimiento edilicio" apps/servicios/fixtures/tipos_servicio.json`
  - `[grep-1]` `grep -n "search_fields" apps/servicios/admin.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check apps/servicios`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-02-modelos-dominio.md modelos-dominio)" 400 apps/servicios`

### T3 — Crear Producto

- **Depende de**: —
- **Puede tocar**: `apps/productos/models.py`, `apps/productos/admin.py`, `apps/productos/migrations/`, `apps/productos/tests/test_models.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/accounts/`, `apps/clientes/`, `apps/sitios/`, `apps/servicios/`, `apps/proyectos/`, migraciones existentes de otras apps
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Task 2: Model Best Practices; `.claude/skills/convenciones-proyecto/SKILL.md` § prohibiciones
- **Worktree**: sí (`worktrees/modelos-dominio-T3`)
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 200 líneas agregadas (incluye la migración autogenerada)
- **Qué hacer**:
  - Producto según §3.9: `nombre_comercial`, `principio_activo`, `registro` (ANMAT/SENASA), `presentacion`, `unidad_dosis_por_defecto`, `activo`.
  - `__str__` con el nombre comercial. Admin con `list_display` y `search_fields`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_models.ProductoTests.test_producto_activo_por_defecto --keepdb`
  - `[existe]` `apps/productos/migrations/0001_initial.py`
  - `[grep-1]` `grep -n "search_fields" apps/productos/admin.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check apps/productos`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-02-modelos-dominio.md modelos-dominio)" 200 apps/productos`

### T4 — Crear Proyecto con estado_visita, encargados empleados e historial

- **Depende de**: T1, T2 (integradas en `main`)
- **Puede tocar**: `apps/proyectos/models.py`, `apps/proyectos/admin.py`, `apps/proyectos/migrations/`, `apps/proyectos/tests/test_models.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/accounts/`, `apps/clientes/`, `apps/sitios/`, `apps/servicios/`, `apps/productos/`, migraciones existentes de otras apps
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Task 2: Model Best Practices; `.claude/skills/convenciones-proyecto/SKILL.md` § prohibiciones
- **Worktree**: no
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 400 líneas agregadas (incluye la migración autogenerada, que duplica la tabla por el historial)
- **Qué hacer**:
  - Proyecto según §3.5:
    - `estado` con choices `activo`, `pausado`, `finalizado`;
    - `frecuencia_dias` como `PositiveIntegerField` opcional;
    - `proxima_visita` como `DateField` opcional;
    - `encargado_inicial` y `encargado_actual` son FK a `settings.AUTH_USER_MODEL` con `on_delete=PROTECT`, `related_name` distintos y `limit_choices_to={"rol": "empleado"}`;
    - `history = HistoricalRecords()`.
  - La constante `UMBRAL_PROXIMA_DIAS = 7` y la property `estado_visita` siguen la regla del Contexto mínimo.
  - Admin con `SimpleHistoryAdmin`, `list_display` y `search_fields`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.proyectos.tests.test_models.ProyectoTests.test_estado_visita_vencida_cuando_proxima_visita_paso --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.proyectos.tests.test_models.ProyectoTests.test_estado_visita_sin_programar_sin_proxima_visita --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.proyectos.tests.test_models.ProyectoTests.test_estado_visita_proxima_dentro_de_siete_dias --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.proyectos.tests.test_models.ProyectoTests.test_estado_visita_al_dia_mas_alla_de_siete_dias --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.proyectos.tests.test_models.ProyectoTests.test_encargado_debe_ser_empleado --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.proyectos.tests.test_models.ProyectoTests.test_historial_registra_cambios --keepdb`
  - `[grep-1]` `grep -n "SimpleHistoryAdmin" apps/proyectos/admin.py`
  - `[grep-1]` `grep -n "UMBRAL_PROXIMA_DIAS = 7" apps/proyectos/models.py`
  - `[existe]` `apps/proyectos/migrations/0001_initial.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check apps/proyectos`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-02-modelos-dominio.md modelos-dominio)" 400 apps/proyectos`

## Trabajo del principal (integración)

Después de la ola 1 y antes de T4, el principal integra:
- revisa `bash .claude/hooks/cambios.sh . main` en cada worktree;
- mergea las ramas `modelos-dominio-T1`, `-T2` y `-T3` a `main`;
- quita los worktrees y borra las ramas;
- corre `git status` y `git worktree list`.

No lleva criterios propios, porque el hook no los ejecuta fuera de `### T<n>`. Lo que comprueba la integración es que los criterios de T1–T3 pasen en la raíz y los de cierre global.

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[grep-0]` `grep -rn "fields = \"__all__\"" apps/`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-02-modelos-dominio.md modelos-dominio`

## Registro de verificación

commit_base: ced3334

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | hecha |
| T2 | hecha |
| T3 | hecha |
| T4 | pendiente |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| 2026-10-02 | T1 | d296031 (worktree) · c4cb9cb (main) | PASA (worktree: verificador 15/15, verificador-b 15/15; main: verificador 15/15) | ruta: delegada · commit T1: d296031 · merge 271a00a |
| 2026-10-02 | T2 | 2215f95 (worktree) · c4cb9cb (main) | PASA (worktree: verificador 11/11, verificador-b 11/11; main: verificador 11/11) | ruta: delegada · commit T2: 2215f95 · merge 23c5055 |
| 2026-10-02 | T3 | a272650 (worktree) · c4cb9cb (main) | PASA (worktree: verificador 6/6, verificador-b 6/6; main: verificador 6/6) | ruta: delegada · commit T3: a272650 · merge c4cb9cb |
| | T4 | | | |
| | TODO | | | |
