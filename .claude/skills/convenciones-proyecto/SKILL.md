---
name: convenciones-proyecto
description: Convenciones y referencia de MAControl (stack, estructura, comandos canónicos, mapa de rutas, variables de entorno, prohibiciones de código); leerla antes de codificar o de citar comandos/rutas del proyecto.
---
# Convenciones del proyecto — MAControl

## Qué es
Repositorio del sitio público de MAControl S.A. (control de plagas, Castelli y Chascomús, Buenos Aires): un proyecto Django que reemplaza a macontrol.com.ar. El contenido sale de la base de datos (`apps.web`) y se edita desde el admin de Django. El panel de gestión, la API y la app móvil viven en otro repositorio.

Fuente de verdad del modelo de contenido: `docs/01-modelo-y-arquitectura.md`. Del contenido público: `docs/00-contenido-fuente.md`. Del diseño: `docs/02-diseno.md`.

## Stack
- Python 3.13 · Django 5.x · `django.contrib.auth.User` (sin modelo de usuario propio)
- PostgreSQL en producción (`DATABASE_URL` obligatoria); en desarrollo, `DATABASE_URL` si está definida y si no SQLite (`db.sqlite3`)
- Templates de Django y CSS escrito a mano (`static/css/web.css`, sin Node ni build); `django-csp` (CSP), `whitenoise` (estáticos) y `gunicorn`
- Pillow (reprocesado de imágenes subidas) · `django-environ` (variables de entorno)
- Calidad: `ruff` (lint + formato), tests con el runner de Django (`manage.py test`)
- `SitioAdministracion.login` (`config/admin.py`) copia `AdminSite.login` de Django 5.2 para usar el mixin de límites (`config/limites.py`): revisarla al actualizar Django

## Estructura
```
config/            settings/{__init__,base,dev,prod}.py · urls.py · asgi/wsgi
                   admin.py (SitioAdministracion) · limites.py (límite de intentos) · red.py (IP del cliente)
apps/
  web/             sitio público: models.py (Servicio, ClienteDestacado, Configuracion, Sector) · admin.py (con vista previa)
                   forms.py · imagenes.py · validators.py · views.py · urls.py · fixtures/contenido_inicial.json
                   templates/web/paginas/ · tests/
templates/web/     base_web.html, 404.html y 500.html
static/            css/web.css, fonts, img (logo y fotos)
herramientas/      humo_web.py (prueba de humo del sitio)
media/             logos de clientes y fotos de servicios (ignorado por git)
docs/              bitácora, decisiones, planes, especificaciones
```
`DJANGO_ENV` (`development` | `production`) elige el módulo de settings en `config/settings/__init__.py`.

### Tabla de propiedad
| Archivo o carpeta | Dueño | Cuándo se toca |
|---|---|---|
| `apps/web/**` | la subtarea de esa parte | en su worktree |
| `config/settings/*.py`, `config/urls.py`, `requirements.txt`, `pyproject.toml` | principal | subtarea de integración, nunca en paralelo |
| `templates/web/base_web.html`, `static/css/web.css` | subtarea "diseño" | las demás la consumen, no la editan |
| `docs/bitacora.md`, `docs/decisiones.md` | principal de cada sesión | solo al cierre, con rebase |
| `docs/planes/<plan>.md` | principal de ese plan | nunca otra sesión |

Una subtarea cuyo `Puede tocar` incluya un archivo de otro dueño es hallazgo bloqueante del `juez-plan`.

### Olas
No hay grafo de dominio: `apps/web` es la única app con migraciones. Las olas se ordenan por dependencia entre subtareas; dentro de una ola todo corre en paralelo y dos subtareas de la misma ola nunca crean migraciones en `apps/web`.

### Worktrees (scripts en `.claude/hooks/`, los usa el principal)
```bash
# Crear: worktrees/<slug>-T<n>, rama <slug>-T<n>, junction venv -> <raíz>/venv, humo manage.py check
bash .claude/hooks/worktree-crear.sh <slug> T<n> [rama_base]
# Integrar: rechaza cambios sin commitear y archivos fuera de las rutas; merge --no-ff ("T<n>: integra <slug>-T<n>"),
# makemigrations --check, test --keepdb; quita la junction, el worktree y la rama
bash .claude/hooks/worktree-integrar.sh <slug> T<n> <rama_destino> <ruta>...
```
`T<n>` acepta sufijo de letra (`T5a`). Dentro de un worktree los comandos canónicos funcionan por la junction `venv`; nunca se toca ni se borra.

Si la prueba de humo de `worktree-crear.sh` falla, la junction queda viva en `worktrees/<slug>-T<n>/venv`. Limpieza: primero `cmd /c rmdir worktrees\<slug>-T<n>\venv` (quita solo la junction) y después `git worktree remove worktrees/<slug>-T<n>`. Nunca `Remove-Item -Recurse` de PowerShell 5.1: sigue la junction y vacía el venv real.

## Comandos canónicos (Windows, desde la raíz)
```bash
# Entorno
python -m venv venv && source venv/Scripts/activate
pip install -r requirements.txt
# Base y servidor
PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py migrate
PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py runserver
# Tests (forma canónica: la misma que usan los criterios de los planes)
PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb
PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.web.tests.test_paginas.PlantillasTests.test_ninguna_plantilla_publica_tiene_form_ni_presupuesto --keepdb -v 2
# Prueba de humo del sitio
./venv/Scripts/python.exe herramientas/humo_web.py
# Tests de hooks (pytest está instalado en el Python del sistema, no en el venv)
py -3 -m pytest .claude/hooks/<archivo>::<función> -q
# Calidad
./venv/Scripts/python.exe -m ruff check .
./venv/Scripts/python.exe -m ruff format .
PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check --deploy
```

## Mapa de rutas
No se mantiene acá la lista completa: la fuente de verdad es `config/urls.py` y `apps/web/urls.py`. Rutas estables:

| Ruta | Qué es | Acceso |
|---|---|---|
| `/` | Home | pública |
| `/servicio/<slug>/` | Página de un servicio publicado (no publicado: 404) | pública |
| `/empresa/` | Datos de la empresa | pública |
| `/contacto/` | Teléfono y WhatsApp | pública |
| `/q/<uuid>/` | Aterrizaje de un QR ya impreso (solo dice "use la app") | pública, sin datos |
| `/sitemap.xml`, `/robots.txt` | SEO | pública |
| `/admin/` | Admin de Django: edición del contenido | sesión + `is_superuser`, con límite de intentos |
| `/admin/web/servicio/<pk>/vista-previa/` | Vista previa de un servicio, publicado o no | admin, `X-Robots-Tag: noindex` |

No hay roles: el único usuario con acceso es el superusuario del admin. Las cuentas se crean con `createsuperuser`; sin autorregistro ni recuperación de contraseña pública.

## Reglas del sitio que el código hace cumplir
- Sin formularios públicos ni "pedir presupuesto"; el contacto es el teléfono y WhatsApp. Ninguna plantilla pública lleva `<form`.
- Contenido real: todo texto, cifra, certificación o cliente sale de `docs/00-contenido-fuente.md` o del usuario. Los datos de la empresa se leen de `Configuracion`.
- Un servicio con `publicado=False` da 404 en `/servicio/<slug>/`; solo la vista previa del admin lo muestra.
- Las imágenes subidas se reprocesan (Pillow, sin EXIF) con los formularios de `apps/web/forms.py`; los ModelAdmin los usan con `form=`.
- `/q/<uuid>/` no consulta la base ni muestra datos: solo indica que se use la app.

## Variables de entorno
- Requeridas: `SECRET_KEY`, `DJANGO_ENV`, `DATABASE_URL` (en producción)
- Opcionales: `ALLOWED_HOSTS` (obligatoria en producción), `CSRF_TRUSTED_ORIGINS`, `MEDIA_ROOT`, `NUM_PROXIES`, `SITE_URL`
- Plantilla: `.env.example` (versionado). `.env` no se versiona y no se lee.

## Prohibiciones de código
- Ninguna regla de negocio en templates ni en `admin.py`.
- Todo dato de contacto o legal del sitio se lee de `Configuracion` (salvo los textos fijos que el diseño aprobado deja en `_respaldos.html` y `servicio.html`).
- Sin `fields = "__all__"` ni `exclude` en formularios que aceptan entrada: los ModelForm declaran `fields`.
- No se escriben migraciones a mano salvo `RunPython` justificado en su docstring.
- Sin `print` en código de aplicación; logging con el logger del módulo.

## Idioma
Docstrings, comentarios, nombres de modelos y campos, textos de interfaz y mensajes de error: en español. Identificadores de librerías y comandos, tal como existen.

## Economía de tokens
- No generar documentación a menos que se solicite; preguntar antes de crear archivos markdown nuevos.
- Docstrings breves, código autodocumentado.
