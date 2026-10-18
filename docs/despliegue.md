# Despliegue en Railway (a mano)

Guía para alojar el sitio público de MAControl. Nada de esto se ejecuta solo: lo hace el usuario desde su cuenta. La configuración ya está en el repositorio (`railway.json`, `.python-version`, `config/settings/prod.py`).

## 1. Cuenta y proyecto
1. Crear la cuenta en railway.com y conectar el repositorio de GitHub.
2. `New Project` -> `Deploy from GitHub repo` -> elegir el repositorio y la rama a alojar.
3. Railway lee `railway.json`:
   - Build: `python manage.py collectstatic --noinput`. Corre con `DJANGO_ENV=production`, así que necesita en el entorno de build las variables que exige `prod.py` (punto 3, marcadas "build"). Railway entrega las variables del servicio a la etapa de build; si falta alguna, el build falla con `ImproperlyConfigured`. Fuente: https://docs.railway.com/builds/build-configuration (consultada el 2026-10-18; no detalla Railpack, confirmarlo en el primer despliegue).
   - Antes de cada despliegue: `python manage.py migrate --noinput` y `python manage.py createcachetable` (tabla `cache_sitio` de la caché compartida; es idempotente).
   - Inicio: `gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 2 --timeout 60`.
4. Python 3.13 sale de `.python-version`. Las dependencias, con versión exacta, salen de `requirements.txt` (`requirements-dev.txt` suma `ruff` y no se instala en el hosting).

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
| `SITE_URL` | obligatoria y con `https://`: `https://demo.up.railway.app` (origen público; arma el canonical, Open Graph y sitemap). Sin ella el arranque aborta |
| `NUM_PROXIES` | obligatoria, entero >= 0 solo con dígitos ASCII; cuántos proxies de confianza hay delante de Django (define la IP del cliente para el límite de intentos del login). Sin ella el arranque aborta. El valor para Railway lo confirma T7 (ver "`NUM_PROXIES` en Railway") |
| `MEDIA_ROOT` | `/data/media` (ruta del volumen, punto 4) |

Variables de build (las lee `collectstatic` al importar `prod.py`): `DJANGO_ENV`, `SECRET_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS`, `SITE_URL` y `NUM_PROXIES`. `CSRF_TRUSTED_ORIGINS`, si está definida, también se valida (solo `https://host`, sin `*` ni ruta).

### `NUM_PROXIES` en Railway
`ip_del_cliente` (`config/red.py`) toma la N-ésima IP desde el final de `X-Forwarded-For`. La documentación de Railway (https://docs.railway.com/networking/public-networking/specs-and-limits, consultada el 2026-10-18) lista entre los encabezados de la petición `X-Real-IP` ("for identifying client's remote IP"), `X-Forwarded-Proto` y `X-Forwarded-Host`; **no menciona `X-Forwarded-For`** ni cuántos saltos agrega el borde. Por eso el valor no se fija acá: lo confirma T7 en el primer despliegue, mirando un `X-Forwarded-For` real, y queda anotado con su fuente. Un valor mal puesto hace que todos los clientes compartan IP (o que el cliente elija la suya).

El dominio público se genera en `Settings` -> `Networking` -> `Generate Domain`. Las variables no se versionan: `.env.example` solo lista los nombres.

## 4. Volumen para `media/`
Los logos de clientes y las fotos de servicios se guardan en disco (`MEDIA_ROOT`). El disco del contenedor se pierde en cada despliegue, así que hace falta un volumen:
1. En el servicio web: `Settings` -> `Volumes` -> `Add Volume`, punto de montaje `/data`.
2. `MEDIA_ROOT=/data/media`.

`/media/` lo sirve la propia aplicación (`apps.web`) desde `MEDIA_ROOT`; no hace falta otro servidor. Sin volumen, las imágenes subidas desaparecen en el siguiente despliegue. Los respaldos del volumen y de Postgres son responsabilidad del usuario.

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
- Valor de `NUM_PROXIES` en Railway: lo confirma T7 (ver arriba). La caché compartida (`DatabaseCache`, tabla `cache_sitio`) y el tope de 3 MB del cuerpo (`LimiteCuerpoMiddleware`) ya están configurados.
