# Despliegue en Railway (a mano)

URL pública: https://web-production-0c499.up.railway.app

Primer despliegue: 2026-10-18 (proyecto Railway `macontrol-web`, servicio `web` desde `WirkraftGruppe/macontrol-web`, rama `main`, Postgres y volumen `web-media` en `/data`). Valores: `NUM_PROXIES=0` (no se usa: con `IP_CLIENTE_CABECERA` definida, `ip_del_cliente` no mira `X-Forwarded-For`; `prod.py` igual la exige) e `IP_CLIENTE_CABECERA=HTTP_X_REAL_IP`, por la documentación de Railway citada en "`NUM_PROXIES` en Railway".

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
| `IP_CLIENTE_CABECERA` | `HTTP_X_REAL_IP` en Railway: nombre de `request.META` (forma `HTTP_[A-Z0-9_]+`) con la IP del cliente que fija el borde; tiene prioridad sobre `NUM_PROXIES`. Si la cabecera falta o no es una IP, se usa `REMOTE_ADDR` |
| `MEDIA_ROOT` | `/data/media` (ruta del volumen, punto 4) |

Variables de build (las lee `collectstatic` al importar `prod.py`): `DJANGO_ENV`, `SECRET_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS`, `SITE_URL` y `NUM_PROXIES`. `CSRF_TRUSTED_ORIGINS`, si está definida, también se valida (solo `https://host`, sin `*` ni ruta).

### `NUM_PROXIES` en Railway
`ip_del_cliente` (`config/red.py`) toma la N-ésima IP desde el final de `X-Forwarded-For`. La documentación de Railway (https://docs.railway.com/networking/public-networking/specs-and-limits, consultada el 2026-10-18) lista entre los encabezados de la petición `X-Real-IP` ("for identifying client's remote IP"), `X-Forwarded-Proto` y `X-Forwarded-Host`; **no menciona `X-Forwarded-For`** ni cuántos saltos agrega el borde. Por eso el valor no se fija acá: lo confirma T7 en el primer despliegue, mirando un `X-Forwarded-For` real, y queda anotado con su fuente. Un valor mal puesto hace que todos los clientes compartan IP (o que el cliente elija la suya).

Por eso en Railway se usa `IP_CLIENTE_CABECERA=HTTP_X_REAL_IP`: `ip_del_cliente` toma la IP de `X-Real-IP`, que documenta Railway, e ignora `X-Forwarded-For` y `NUM_PROXIES`. Que el borde pise un `X-Real-IP` enviado por el cliente se comprueba en el primer despliegue (T7) con fallos de login que falsifican la cabecera: si con IP falsas distintas el sexto fallo del mismo usuario no da 429, el borde no la pisa y el despliegue no sigue. El resultado queda anotado acá.

Resultado del 2026-10-18 (cada POST con la cookie y el token CSRF de un GET previo, usuarios inventados `prueba-borde-*`):
- Control positivo: 6 fallos del mismo usuario, cada uno con `X-Real-IP` y `X-Forwarded-For` falsos y distintos (y una variante con dos `X-Real-IP` por pedido): 200 cinco veces y 429 en el sexto. El cliente no elige su balde.
- Control negativo: con el balde de `prueba-borde-n` lleno desde una red, un fallo del mismo usuario desde otra red real (datos móviles) mostró el formulario con error, no el 429. Los clientes no comparten la IP del proxy.
Conclusión: el borde pisa `X-Real-IP` con la IP real del cliente.

El dominio público se genera en `Settings` -> `Networking` -> `Generate Domain`. Las variables no se versionan: `.env.example` solo lista los nombres.

## 4. Volumen para `media/`
Los logos de clientes y las fotos de servicios se guardan en disco (`MEDIA_ROOT`). El disco del contenedor se pierde en cada despliegue, así que hace falta un volumen:
1. En el servicio web: `Settings` -> `Volumes` -> `Add Volume`, punto de montaje `/data`.
2. `MEDIA_ROOT=/data/media`.

`/media/` lo sirve la propia aplicación (`apps.web`) desde `MEDIA_ROOT`; no hace falta otro servidor. Sin volumen, las imágenes subidas desaparecen en el siguiente despliegue. Los respaldos del volumen y de Postgres son responsabilidad del usuario.

## 5. Primer despliegue: base nueva
El sitio arranca con una base nueva, sin datos de otro sistema. En el primer despliegue del 2026-10-18 el `preDeployCommand` de `railway.json` (array de dos comandos) **no se ejecutó**: no hubo tablas y `/` dio 500 hasta correr `migrate` y `createcachetable` a mano por `railway ssh` (P-puesta-en-produccion-9). Hasta corregirlo, después de un despliegue con migraciones nuevas hay que correrlas así. El resto se hace una vez desde la consola del servicio (`railway ssh` o la pestaña de comandos):
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
- IP del cliente en Railway: resuelta con `IP_CLIENTE_CABECERA=HTTP_X_REAL_IP` y comprobada el 2026-10-18 (ver arriba).
- `preDeployCommand` que no se ejecuta en Railway (P-puesta-en-produccion-9). La caché compartida (`DatabaseCache`, tabla `cache_sitio`) y el tope de 3 MB del cuerpo (`LimiteCuerpoMiddleware`) ya están configurados.
