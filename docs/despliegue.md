# Despliegue en Railway (a mano)

Guía para alojar el sitio público de MAControl. Nada de esto se ejecuta solo: lo hace el usuario desde su cuenta. La configuración ya está en el repositorio (`railway.json`, `.python-version`, `config/settings/prod.py`).

## 1. Cuenta y proyecto
1. Crear la cuenta en railway.com y conectar el repositorio de GitHub.
2. `New Project` -> `Deploy from GitHub repo` -> elegir el repositorio y la rama a alojar.
3. Railway lee `railway.json`:
   - Build: `python manage.py collectstatic --noinput`.
   - Antes de cada despliegue: `python manage.py migrate --noinput`.
   - Inicio: `gunicorn config.wsgi --bind 0.0.0.0:$PORT --timeout 60`.
4. Python 3.13 sale de `.python-version`.

## 2. Base de datos
1. En el proyecto: `New` -> `Database` -> `Add PostgreSQL`.
2. En el servicio web, variable `DATABASE_URL` como referencia a la base: `${{Postgres.DATABASE_URL}}`.

## 3. Variables del servicio web
| Variable | Valor |
|---|---|
| `DJANGO_ENV` | `production` (obligatoria; con `development` el arranque aborta en Railway) |
| `SECRET_KEY` | una clave larga y aleatoria, propia de esta instancia |
| `DATABASE_URL` | referencia a Postgres (punto 2) |
| `ALLOWED_HOSTS` | el dominio público, p. ej. `demo.up.railway.app` (si queda vacío, el arranque aborta) |
| `CSRF_TRUSTED_ORIGINS` | el mismo dominio con esquema, p. ej. `https://demo.up.railway.app` (varios, separados por comas) |
| `SITE_URL` | `https://demo.up.railway.app` (origen público del sitio) |
| `MEDIA_ROOT` | `/data/media` (ruta del volumen, punto 4) |

El dominio público se genera en `Settings` -> `Networking` -> `Generate Domain`. Las variables no se versionan: `.env.example` solo lista los nombres.

## 4. Volumen para `media/`
Los logos de clientes y las fotos de servicios se guardan en disco (`MEDIA_ROOT`). El disco del contenedor se pierde en cada despliegue, así que hace falta un volumen:
1. En el servicio web: `Settings` -> `Volumes` -> `Add Volume`, punto de montaje `/data`.
2. `MEDIA_ROOT=/data/media`.

Sin volumen, las imágenes subidas desaparecen en el siguiente despliegue. Los respaldos del volumen y de Postgres son responsabilidad del usuario.

## 5. Primer despliegue: base nueva
El sitio arranca con una base nueva, sin datos de otro sistema. El `preDeployCommand` ya corre `migrate`; el resto se hace una vez desde la consola del servicio (`railway ssh` o la pestaña de comandos):
```bash
python manage.py migrate --noinput
python manage.py loaddata contenido_inicial
python manage.py createsuperuser
```
- `loaddata contenido_inicial` carga la configuración de la empresa, los 9 servicios y los clientes (`apps/web/fixtures/contenido_inicial.json`). Se corre una sola vez: volver a correrlo pisa lo editado desde el admin.
- `createsuperuser` crea la única cuenta con acceso a `/admin/`. No hay otras cuentas ni autorregistro.
- Después se entra a `/admin/`, se completan los datos de la empresa y se suben las fotos y los logos.

## 6. Pendientes de `despliegue` que siguen abiertos
Esta configuración no los cierra. Listarlos con:

```bash
py -3 .claude/hooks/pendientes.py
```

Los de más peso antes de abrir la instancia al público:
- `NUM_PROXIES` y `CACHES` compartida: detrás del proxy de Railway todas las peticiones comparten IP, y el límite de intentos del login del admin cuenta por IP.
- Servido de `media/` en producción: `DEBUG=False` no sirve `MEDIA_URL`, y las imágenes subidas no se ven hasta resolverlo.
- Tope de bytes de las subidas en el proxy o con un middleware.
