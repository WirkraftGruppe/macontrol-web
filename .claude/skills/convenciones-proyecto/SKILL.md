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
templates/         base.html · panel/ · web/ · pdf/
static/            css compilado, htmx, leaflet, logo
media/             fotos, logos, QR (ignorado por git)
docs/              bitácora, decisiones, planes, especificaciones
```
`DJANGO_ENV` (`development` | `production`) elige el módulo de settings en `config/settings/__init__.py`.

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

Para ver las rutas de una app: `grep -n "path(" apps/<app>/urls.py`.

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
