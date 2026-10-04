---
name: convenciones-proyecto
description: Convenciones y referencia de MAControl (stack, estructura de apps, comandos canónicos, mapa de rutas, roles, variables de entorno, prohibiciones de código); leerla antes de codificar o de citar comandos/rutas del proyecto.
---

# Convenciones del proyecto — MAControl

## Qué es
Sistema de MAControl S.A. (control de plagas, Castelli y Chascomús, Buenos Aires) en un único proyecto Django:
- **Sitio público** `/` — reemplaza a macontrol.com.ar. Contenido desde base de datos (`apps.web`).
- **Panel de gestión** `/panel/` — administradores: clientes, sitios con QR, proyectos, visitas, mapa, productos, certificados.
- **API** `/api/v1/` — para la app móvil de los empleados (Expo, etapa final) y para el mapa del panel.

Fuente de verdad del dominio: `docs/01-modelo-y-arquitectura.md`. Del contenido público: `docs/00-contenido-fuente.md`. Del diseño: `docs/02-diseno.md`.

## Stack
- Python 3.13 · Django 5.x · Django REST Framework · `djangorestframework-simplejwt`
- PostgreSQL en producción (`DATABASE_URL` obligatoria); en desarrollo, `DATABASE_URL` si está definida y si no SQLite (`db.sqlite3`)
- Templates de Django + Tailwind CSS (CLI, sin Node en producción) + HTMX + Leaflet/OpenStreetMap
- WeasyPrint (PDF: certificados, informes, historial, etiquetas QR) · `segno` (QR) · Pillow (fotos)
- `django-simple-history` (auditoría de Sitio, Proyecto, Visita) · `django-storages` (fotos, backend intercambiable)
- Calidad: `ruff` (lint + formato), tests con el runner de Django (`manage.py test`)
- `SitioAdministracion.login` (`config/admin.py`) copia `AdminSite.login` de Django 5.2 para usar el mixin de límites: revisarla al actualizar Django

## Estructura
```
config/            settings/{__init__,base,dev,prod}.py · urls.py · asgi/wsgi
apps/
  accounts/        User (rol: administrador | empleado), login del panel, JWT de la API
  clientes/        Cliente
  sitios/          Sitio (lat/lng, sector, qr_codigo UUID), etiqueta QR
  servicios/       TipoServicio, CampoPlanilla (planilla dinámica por servicio)
  proyectos/       Proyecto (estado, frecuencia, próxima visita, encargados)
  visitas/         Visita, Foto, ProductoAplicado; reglas que actualizan el proyecto
  productos/       Producto (catálogo con registro ANMAT/SENASA)
  informes/        Certificado, informes PDF, historial del empleado
  panel/           vistas del panel (Django + HTMX)
  api/             DRF: serializers, viewsets, auth, `v1/`
  web/             sitio público: páginas de servicio, configuración, clientes destacados
templates/         solo base.html y panel/base.html (el resto vive en cada app)
static/            css compilado, htmx, leaflet, logo
media/             fotos, logos, QR (ignorado por git)
docs/              bitácora, decisiones, planes, especificaciones
```
`DJANGO_ENV` (`development` | `production`) elige el módulo de settings en `config/settings/__init__.py`.

### Estructura de cada app de dominio
Cada app es dueña de todo lo suyo, con nombres de archivo fijos (así la propiedad se verifica con `grep`):
```
apps/<app>/
  models.py · services.py · admin.py · migrations/
  serializers.py · api_views.py · api_urls.py          # lo de la API
  panel_views.py · panel_urls.py · panel_forms.py      # lo del panel
  templates/<app>/panel/… · templates/<app>/pdf/…      # con APP_DIRS; nada en templates/<app>
  tests/test_models.py · test_services.py · test_api.py · test_panel.py
```
- `api_urls.py` y `panel_urls.py` declaran `app_name = "<app>"`.
- `apps/api/urls.py` y `apps/panel/urls.py` son routers de una línea por app: `path("sitios/", include("apps.sitios.api_urls"))`.
- `apps/api` conserva solo lo transversal (JWT, permisos base, paginación, excepciones); `apps/panel`, el layout, el login, el tablero y el mapa agregado.
- `apps/web` es el sitio público entero y se paraleliza por página (home, servicio, empresa), no por dominio. `apps/informes` es transversal pero expone sus propios `api_urls` y `panel_urls`.

### Tabla de propiedad
| Archivo o carpeta | Dueño | Cuándo se toca |
|---|---|---|
| `apps/<app>/**` | la subtarea de esa app | en su worktree |
| `config/settings/*.py`, `config/urls.py`, `requirements.txt`, `pyproject.toml` | principal | subtarea de integración, nunca en paralelo |
| `apps/api/urls.py`, `apps/panel/urls.py` | principal | al integrar cada ola |
| `apps/api/**` (salvo `urls.py`), `apps/panel/**` (salvo `urls.py`) | subtarea "transversal" del plan que lo necesite | una por plan |
| `templates/base.html`, `templates/panel/base.html`, `static/src/**`, `static/css/**` | subtarea "diseño" | los implementadores de dominio la consumen, no la editan |
| `docs/bitacora.md`, `docs/decisiones.md` | principal de cada sesión | solo al cierre, con rebase |
| `docs/planes/<plan>.md` | principal de ese plan | nunca otra sesión |

Una subtarea cuyo `Puede tocar` incluya un archivo de otro dueño es hallazgo bloqueante del `juez-plan`.

### Olas por grafo de FK
```
Ola 1: accounts, clientes, servicios, productos    (sin FK entre sí)
Ola 2: sitios        → clientes
Ola 3: proyectos     → sitios, servicios, accounts
Ola 4: visitas       → proyectos, productos, accounts
Ola 5: informes      → visitas, clientes
```
Dentro de una ola, todo en paralelo; dos subtareas de la misma ola nunca crean migraciones en la misma app.

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
PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_qr.ResolverQRTests.test_qr_inexistente_da_404 --keepdb -v 2
# Tests de hooks (pytest está instalado en el Python del sistema, no en el venv)
py -3 -m pytest .claude/hooks/<archivo>::<función> -q
# Calidad
./venv/Scripts/python.exe -m ruff check .
./venv/Scripts/python.exe -m ruff format .
PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check --deploy
# Tailwind
npx tailwindcss -i static/src/input.css -o static/css/app.css --watch
```

## Mapa de rutas
No se mantiene acá la lista de endpoints: la fuente de verdad es `config/urls.py` y el `urls.py` de cada app. Prefijos estables:

| Prefijo | Qué es | Auth |
|---|---|---|
| `/` | Sitio público (`apps.web`) | pública |
| `/q/<uuid>/` | Página de aterrizaje de un QR abierto en un navegador (solo dice "use la app") | pública, sin datos |
| `/panel/` | Panel de gestión (`apps.panel`) | sesión Django + rol administrador |
| `/admin/` | Admin técnico de Django | sesión + `is_superuser` |
| `/api/v1/` | API (`apps.api`) | JWT; empleados y administradores |

Para ver las rutas de una app: `grep -n "path(" apps/<app>/api_urls.py apps/<app>/panel_urls.py`.

## Roles (`apps/accounts`)
- `User.rol` ∈ {`administrador`, `empleado`}; properties `es_administrador`, `es_empleado`.
- **Administrador**: panel completo. **Empleado**: solo la API; ve sus visitas asignadas, resuelve QR, crea visitas realizadas, consulta y descarga su historial.
- `is_staff` **solo** habilita `/admin/`; no significa "administrador del panel". El panel exige `rol == administrador` con su propio mixin; la API exige el rol en cada permission class.
- Las cuentas se crean a mano desde el panel o el admin; sin autorregistro, sin recuperación de contraseña pública en etapa 1.

## Reglas de dominio que el código hace cumplir
- Una visita con `origen=app` solo se crea a partir de un `qr_codigo` válido de un sitio activo, con geolocalización y al menos una foto. Sin QR válido la API responde 4xx; no hay ruta alternativa para el empleado.
- Una visita con `origen=manual` solo la crea un administrador y lleva `motivo_manual` obligatorio.
- Al guardar una visita realizada: `proyecto.encargado_actual = visita.empleado`, `proyecto.actualizado = now()`, y si `frecuencia_dias` está definida, `proxima_visita = realizada_en + frecuencia_dias`. Esta regla vive en un servicio de `apps/visitas/` (no en la vista ni en el serializer) y tiene test.
- `ProductoAplicado.producto` siempre apunta al catálogo; la API no acepta nombres libres de producto.
- Un `Certificado` emitido no se edita; una corrección emite uno nuevo con `reemplaza_a`.
- El sitio público no tiene formularios que envíen correo ni "pedir presupuesto"; el contacto es el teléfono y WhatsApp.

## Variables de entorno
- Requeridas: `SECRET_KEY`, `DJANGO_ENV`, `DATABASE_URL`
- Opcionales: `ALLOWED_HOSTS`, `MEDIA_ROOT`, `STORAGE_BACKEND` (`local` | `s3`), `AWS_*` cuando `s3`, `SITE_URL` (base para el contenido de los QR)
- Plantilla: `.env.example` (versionado). `.env` no se versiona y no se lee.

## Prohibiciones de código
- Todo serializer de escritura declara `fields` explícitos; `fields = "__all__"` y `exclude` son hallazgo (mass assignment).
- Ningún queryset de la API devuelve visitas de otro empleado a un empleado: `get_queryset()` filtra por `request.user` salvo rol administrador. `if user.is_staff` nunca decide acceso a datos.
- Ninguna regla de negocio en templates ni en `admin.py`; van en `services.py` de la app que corresponde.
- Coordenadas y fotos son datos personales de los empleados (dónde estuvieron y cuándo): no se exponen en el sitio público ni en `/q/<uuid>/`, y no se registran en logs.
- No se escriben migraciones a mano salvo `RunPython` justificado en su docstring.
- Sin `print` en código de aplicación; logging con el logger del módulo.

## Idioma
Docstrings, comentarios, nombres de modelos y campos, textos de interfaz y mensajes de error: en español. Identificadores de librerías y comandos, tal como existen.

## Economía de tokens
- No generar documentación a menos que se solicite; preguntar antes de crear archivos markdown nuevos.
- Docstrings breves, código autodocumentado.
