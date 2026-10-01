# Plan: esqueleto del proyecto Django

- **slug**: `esqueleto`
- **fecha**: 2026-10-01
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): esqueleto`. No se escribe acá: el
  hash se anota en `## Registro de verificación`.
- **objetivo**: el proyecto Django arranca (`check`, migraciones y tests en verde) con las once apps, `accounts.User` con rol y la plantilla base con los tokens visuales, listo para los planes de dominio.
- **fuera de alcance**: modelos distintos de `User`; vistas reales; panel; API; serializers; Tailwind compilado; despliegue; `docker-compose.yml`; app móvil.
- **áreas**: dominio (modelos y servicios) | infraestructura
- **seguridad**: sí — `accounts.User` y roles, `config/settings/prod.py` (SECRET_KEY, DATABASE_URL, cabeceras seguras) y vistas provisorias públicas en `/panel/` y `/api/v1/`; corre también `auditor-seguridad`.

## Contexto mínimo

El repositorio solo tiene documentación y el esquema de agentes (commits `cc91d90`, `e5a023a`, `52f2098`); no hay código Django. Este plan sale de `docs/prompts/00-arranque.md` y crea la estructura de `docs/01-modelo-y-arquitectura.md` §5 con las decisiones técnicas de §6.
Decisiones aplicadas (`docs/decisiones.md`, 2026-10-01): Python 3.13 (venv ya creado en `./venv`, sin paquetes); en desarrollo la base es `DATABASE_URL` si está definida y si no SQLite `db.sqlite3`; producción exige `DATABASE_URL`; `.env` no se lee (convenciones-proyecto § Variables de entorno); `User.activo` se cubre con `is_active`.
Roles: `.claude/skills/convenciones-proyecto/SKILL.md` § Roles (`is_staff` solo habilita `/admin/`).
Tokens visuales: `docs/02-diseno.md` (tablas de color, tema oscuro = web, claro = panel).
El logo provisorio está en `images-for-content/image-logo.png` (carpeta no versionada); no existe "Logo Imagen.png".

## Subtareas

### T1 — Crear la base del proyecto y el modelo accounts.User con rol

- **Depende de**: —
- **Puede tocar**: `requirements.txt`, `pyproject.toml`, `.env.example`, `manage.py`, `config/` (todo), `apps/__init__.py`, `apps/accounts/` (todo), `templates/.gitkeep`, `static/.gitkeep`; instalar paquetes en `./venv`
- **No puede tocar**: `docs/`, `.claude/`, `.agents/`, `CLAUDE.md`, `.gitignore`, `.gitattributes`, cualquier otra app de `apps/`
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` (settings y models), `.agents/skills/django-security/SKILL.md` (settings de producción), `.claude/skills/convenciones-proyecto/SKILL.md`
- **Worktree**: no
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 500 líneas agregadas (incluye la migración autogenerada)
- **Qué hacer**:
  - `requirements.txt` con Django 5.2.x, djangorestframework, djangorestframework-simplejwt, psycopg[binary], django-environ, django-simple-history, django-storages, Pillow, WeasyPrint, segno, ruff; instalarlo en `./venv`. `pyproject.toml` con la configuración de ruff (target py313; `extend-exclude` con `venv`, `worktrees`, `.agents`, `.claude` y `**/migrations`: las skills y los hooks no son código de la aplicación).
  - `config/settings/{__init__,base,dev,prod}.py`: `__init__` elige `dev` o `prod` según `DJANGO_ENV` (`development` | `production`); variables con `django-environ` leyendo solo del entorno (sin `read_env`). `dev.py`: `DEBUG=True`, `SECRET_KEY` y `DATABASE_URL` con valores por defecto de desarrollo (SQLite `db.sqlite3`). `prod.py`: `SECRET_KEY = env("SECRET_KEY")` y `DATABASES = {"default": env.db("DATABASE_URL")}` sin valor por defecto (django-environ responde `Set the <VAR> environment variable`), `DEBUG=False`, cookies seguras, HSTS, `SECURE_PROXY_SSL_HEADER`. `LANGUAGE_CODE="es-ar"`, `TIME_ZONE="America/Argentina/Buenos_Aires"`. `TEMPLATES[0]["DIRS"] = [BASE_DIR / "templates"]` y `STATICFILES_DIRS = [BASE_DIR / "static"]` (crear `templates/.gitkeep` y `static/.gitkeep` si hace falta para `check`). `config/urls.py` solo con `/admin/`; `wsgi.py` y `asgi.py`. `config/settings/base.py` y `config/urls.py` se presupuestan en T2, que los termina.
  - `apps/accounts`: `User(AbstractUser)` con `rol` (TextChoices `administrador` | `empleado`, por defecto `empleado`), `telefono` (opcional), properties `es_administrador` y `es_empleado`; `AUTH_USER_MODEL = "accounts.User"`; admin registrado con `UserAdmin`; migración `0001_initial` generada con `makemigrations`.
  - `.env.example` con las variables de convenciones-proyecto § Variables de entorno.
  - Tests en `apps/accounts/tests/test_user.py`, clase `UserTests`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_user.UserTests.test_rol_administrador_y_empleado_son_excluyentes --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_user.UserTests.test_is_staff_no_implica_administrador --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_user.UserTests.test_rol_por_defecto_es_empleado --keepdb`
  - `[grep-1]` `grep -n "AUTH_USER_MODEL = \"accounts.User\"" config/settings/base.py`
  - `[grep-0]` `grep -rn "read_env" config/`
  - `[existe]` `.env.example`
  - `[existe]` `apps/accounts/migrations/0001_initial.py`
  - `[cmd]` `out="$(env -u SECRET_KEY DATABASE_URL=sqlite:///prod-check.sqlite3 PYTHONIOENCODING=utf-8 DJANGO_ENV=production ./venv/Scripts/python.exe manage.py check 2>&1)"; test $? -ne 0 && echo "$out" | grep -q "Set the SECRET_KEY environment variable"`
  - `[cmd]` `out="$(env -u DATABASE_URL SECRET_KEY=clave-de-prueba-larga-0123456789-abcdefghijklmnopqrstuvwxyz PYTHONIOENCODING=utf-8 DJANGO_ENV=production ./venv/Scripts/python.exe manage.py check 2>&1)"; test $? -ne 0 && echo "$out" | grep -q "Set the DATABASE_URL environment variable"`
  - `[cmd]` `SECRET_KEY=clave-de-prueba-larga-0123456789-abcdefghijklmnopqrstuvwxyz DATABASE_URL=sqlite:///prod-check.sqlite3 ALLOWED_HOSTS=macontrol.com.ar PYTHONIOENCODING=utf-8 DJANGO_ENV=production ./venv/Scripts/python.exe manage.py check`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts --keepdb`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-01-esqueleto.md esqueleto)" 500 requirements.txt pyproject.toml .env.example manage.py config ':(exclude)config/settings/base.py' ':(exclude)config/urls.py' templates/.gitkeep static/.gitkeep apps/__init__.py apps/accounts`

### T2 — Crear las otras diez apps y los prefijos de URL con vistas provisorias

- **Depende de**: T1
- **Puede tocar**: `apps/clientes/`, `apps/sitios/`, `apps/servicios/`, `apps/proyectos/`, `apps/visitas/`, `apps/productos/`, `apps/informes/`, `apps/panel/`, `apps/api/`, `apps/web/`, `config/settings/base.py` (solo `INSTALLED_APPS`), `config/urls.py`
- **No puede tocar**: `docs/`, `.claude/`, `.agents/`, `apps/accounts/`, `requirements.txt`, `config/settings/dev.py`, `config/settings/prod.py`
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` (apps y urls), `.claude/skills/convenciones-proyecto/SKILL.md` § Estructura y § Mapa de rutas
- **Worktree**: no
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 550 líneas agregadas (400 de T2 más ≈150 de `config/settings/base.py` y `config/urls.py`, que crea T1 y termina T2; cada subtarea mide rutas disjuntas para que los criterios de las anteriores sigan valiendo)
- **Qué hacer**:
  - Cada una de las diez apps con `__init__.py`, `apps.py` (`name = "apps.<app>"`, `verbose_name` en español), `models.py` sin modelos, `urls.py` y `tests/__init__.py`; registrarlas en `INSTALLED_APPS`.
  - Vistas provisorias que responden 200 con un texto fijo y sin datos: `/` y `/q/<uuid:codigo>/` en `apps.web` (el QR dice "Sitio de MAControl S.A. — use la app"), `/panel/` en `apps.panel`, `/api/v1/` en `apps.api`. `config/urls.py` incluye cada `urls.py` con su prefijo.
  - Tests en `apps/web/tests/test_rutas.py`, clase `RutasTests`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_rutas.RutasTests.test_raiz_responde_200 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_rutas.RutasTests.test_q_uuid_responde_200 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_rutas.RutasTests.test_q_no_uuid_da_404 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_rutas.RutasTests.test_panel_responde_200 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_rutas.RutasTests.test_api_v1_responde_200 --keepdb`
  - `[existe]` `apps/clientes/apps.py`
  - `[existe]` `apps/sitios/apps.py`
  - `[existe]` `apps/servicios/apps.py`
  - `[existe]` `apps/proyectos/apps.py`
  - `[existe]` `apps/visitas/apps.py`
  - `[existe]` `apps/productos/apps.py`
  - `[existe]` `apps/informes/apps.py`
  - `[existe]` `apps/panel/apps.py`
  - `[existe]` `apps/api/apps.py`
  - `[existe]` `apps/web/apps.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-01-esqueleto.md esqueleto)" 550 apps/clientes apps/sitios apps/servicios apps/proyectos apps/visitas apps/productos apps/informes apps/panel apps/api apps/web ':(exclude)apps/web/tests/test_base.py' config/settings/base.py config/urls.py`

### T3 — Crear templates/base.html con los tokens de diseño y el logo

- **Depende de**: T2
- **Puede tocar**: `templates/base.html`, `static/img/logo.png`, `apps/web/tests/test_base.py`
- **No puede tocar**: `docs/`, `.claude/`, `.agents/`, `images-for-content/`, `config/` (T1 ya configuró `TEMPLATES` y `STATICFILES_DIRS`), cualquier otro archivo de `apps/`
- **Skill a leer antes**: `.agents/skills/frontend-design/SKILL.md`, `docs/02-diseno.md`
- **Worktree**: no
- **Ruta**: delegada · Evidencia: … · Commit: …
- **Presupuesto**: 300 líneas agregadas
- **Qué hacer**:
  - `templates/base.html`: HTML5 en español, todos los tokens de color de `docs/02-diseno.md` como variables CSS bajo `[data-tema="oscuro"]` y `[data-tema="claro"]` (los de estado compartidos en `:root`), fuentes Barlow / Barlow Condensed, bloques `title`, `contenido` y `extra_head`; `data-tema` por defecto `oscuro` sobreescribible desde un bloque.
  - Copiar `images-for-content/image-logo.png` a `static/img/logo.png` y referenciarlo con `{% static %}`.
  - Test en `apps/web/tests/test_base.py`, clase `BaseTemplateTests`, que renderiza `base.html` y comprueba ambos temas.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_base.BaseTemplateTests.test_base_define_tokens_de_ambos_temas --keepdb`
  - `[grep-1]` `grep -n -- "--brand: #ffc600" templates/base.html`
  - `[grep-1]` `grep -n "data-tema=\"claro\"" templates/base.html`
  - `[existe]` `static/img/logo.png`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . "$(bash .claude/hooks/congelado.sh docs/planes/2026-10-01-esqueleto.md esqueleto)" 300 templates/base.html static/img apps/web/tests/test_base.py`

## Trabajo del principal (integración)

Nada: las subtareas son secuenciales y cada una deja el proyecto integrado. La verificación final corre directo.

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[grep-0]` `grep -rn "fields = \"__all__\"" apps/`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-01-esqueleto.md esqueleto`

## Registro de verificación

commit_base: 37f1ec7

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | hecha |
| T2 | pendiente |
| T3 | pendiente |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| 2026-10-01 | T1 | fb08f0f | PASA (verificador 15/15; verificador-b 15/15) | ruta: delegada · commit T1: fb08f0f |
| | T2 | | | |
| | T3 | | | |
| | TODO | | | |
