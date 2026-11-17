# Despliegue en Railway

URL pública: https://www.macontrol.com.ar. El `*.up.railway.app` del servicio es solo su dominio de servicio, no la dirección del sitio.

Primer despliegue: 2026-10-18 (proyecto Railway `macontrol-web`, servicio `web` desde `WirkraftGruppe/macontrol-web`, rama `main`, Postgres y volumen `web-media` en `/data`).

Guía para alojar el sitio público de MAControl. Nada de esto se ejecuta solo: lo hace el usuario desde su cuenta. La configuración del servicio `web` vive en `.railway/railway.ts`; además intervienen `.python-version` y `config/settings/prod.py`.

## 1. Cuenta, proyecto y configuración del servicio
1. Crear la cuenta en railway.com y conectar el repositorio de GitHub.
2. `New Project` -> `Deploy from GitHub repo` -> elegir el repositorio y la rama a alojar.
3. La configuración del servicio `web` está en `.railway/railway.ts` (TypeScript; paquete npm `railway` en versión exacta, fijada en `.railway/package.json`). La primera vez, instalar las dependencias con `npm ci --prefix .railway`. **Railway no lee `.railway/` al desplegar**: el archivo se aplica con la CLI (punto 4). Declara:
   - Build con Railpack: `python manage.py collectstatic --noinput`. Corre con `DJANGO_ENV=production`, así que necesita en el entorno de build las variables que exige `prod.py` (punto 3, marcadas "build"). Railway entrega las variables del servicio a la etapa de build; si falta alguna, el build falla con `ImproperlyConfigured`.
   - Comando previo (`preDeployCommand`): `python manage.py migrate --noinput && python manage.py createcachetable` (`cache_sitio` es la tabla de la caché compartida; el comando es idempotente).
   - Arranque: `gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 2 --timeout 60`.
   - Volumen `web-media` montado en `/data`.
   - Las variables **no** las gestiona (`variables: { managed: false }`): siguen en Railway y se editan allí.
   - Política de reinicio: la de la plataforma (`ON_FAILURE`, 10 reintentos); no se declara.
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
| `ALLOWED_HOSTS` | el dominio público, p. ej. `www.macontrol.com.ar` (si queda vacío, el arranque aborta) |
| `CSRF_TRUSTED_ORIGINS` | el mismo dominio con esquema, p. ej. `https://www.macontrol.com.ar` (varios, separados por comas) |
| `SITE_URL` | obligatoria y con `https://`: `https://www.macontrol.com.ar` (origen público; arma el canonical, Open Graph y sitemap). Sin ella el arranque aborta |
| `NUM_PROXIES` | `0`. `prod.py` la exige (entero >= 0 solo con dígitos ASCII), pero en Railway no se usa: con `IP_CLIENTE_CABECERA` definida, `ip_del_cliente` no mira `X-Forwarded-For` |
| `IP_CLIENTE_CABECERA` | `HTTP_X_REAL_IP` en Railway: nombre de `request.META` (forma `HTTP_[A-Z0-9_]+`) con la IP del cliente que fija el borde; tiene prioridad sobre `NUM_PROXIES`. Si la cabecera falta o no es una IP, se usa `REMOTE_ADDR` |
| `MEDIA_ROOT` | `/data/media` (ruta del volumen, punto 5) |

Variables de build (las lee `collectstatic` al importar `prod.py`): `DJANGO_ENV`, `SECRET_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS`, `SITE_URL` y `NUM_PROXIES`. `CSRF_TRUSTED_ORIGINS`, si está definida, también se valida (solo `https://host`, sin `*` ni ruta).

Las variables no se versionan: `.env.example` solo lista los nombres.

### IP del cliente en Railway
La documentación de Railway (https://docs.railway.com/networking/public-networking/specs-and-limits, consultada el 2026-10-18) lista entre los encabezados de la petición `X-Real-IP` ("for identifying client's remote IP"), `X-Forwarded-Proto` y `X-Forwarded-Host`; no menciona `X-Forwarded-For`. Por eso en Railway se usa `IP_CLIENTE_CABECERA=HTTP_X_REAL_IP`: `ip_del_cliente` (`config/red.py`) toma la IP de `X-Real-IP` e ignora `X-Forwarded-For` y `NUM_PROXIES`.

Resultado de la prueba del 2026-10-18 (cada POST con la cookie y el token CSRF de un GET previo, usuarios inventados `prueba-borde-*`):
- Control positivo: 6 fallos del mismo usuario, cada uno con `X-Real-IP` y `X-Forwarded-For` falsos y distintos (y una variante con dos `X-Real-IP` por pedido): 200 cinco veces y 429 en el sexto. El cliente no elige su balde.
- Control negativo: con el balde de `prueba-borde-n` lleno desde una red, un fallo del mismo usuario desde otra red real (datos móviles) mostró el formulario con error, no el 429. Los clientes no comparten la IP del proxy.

Conclusión: el borde pisa `X-Real-IP` con la IP real del cliente.

## 4. Cambiar la configuración y aplicarla
Un `git push` a `main` despliega el código, no la configuración. Para cambiar la configuración:
1. Editar `.railway/railway.ts`.
2. `railway status`: debe decir `macontrol-web`. Si dice otro proyecto, no seguir.
3. `railway config plan`: revisar la salida. Debe terminar con `0 to destroy`. Si propone borrar o recrear Postgres, el volumen o el servicio, no aplicar.
4. `railway config apply`.

`railway config plan --detailed-exit-code` sale con 0 si la configuración está al día y con 2 si hay cambios pendientes.

### Comando previo
El `preDeployCommand` corre en un contenedor aparte, sin volúmenes, con las variables y la red privada del servicio. Es idempotente. Si falla, el despliegue no avanza y queda el anterior. Fuente: https://docs.railway.com/guides/pre-deploy-command.

### Correr comandos en producción
1. Primero `railway status`: el 2026-11-17 la CLI de esta carpeta estaba vinculada a otro proyecto.
2. Ejecutar:
```bash
railway ssh -s web -- sh -c 'cd /app && /app/.venv/bin/python manage.py <comando>'
```
3. En Git Bash anteponer `MSYS_NO_PATHCONV=1` al comando (evita que convierta las rutas `/app/...` en rutas de Windows). En PowerShell no hace falta.

## 5. Volumen para `media/`
Los logos de clientes y las fotos de servicios se guardan en disco (`MEDIA_ROOT`). El disco del contenedor se pierde en cada despliegue, así que hace falta un volumen: `web-media`, montado en `/data` (declarado en `.railway/railway.ts`) y con `MEDIA_ROOT=/data/media`.

`/media/` lo sirve la propia aplicación (`apps.web`) desde `MEDIA_ROOT`; no hace falta otro servidor. Sin volumen, las imágenes subidas desaparecen en el siguiente despliegue. Los respaldos del volumen y de Postgres son responsabilidad del usuario.

## 6. Primer despliegue: base nueva
El sitio arranca con una base nueva, sin datos de otro sistema. `migrate` y `createcachetable` los corre el comando previo (punto 1). El resto se hace una vez, desde la consola del servicio (forma de correr comandos: punto 4):
```bash
python manage.py loaddata contenido_inicial
python manage.py createsuperuser
```
- `loaddata contenido_inicial` carga la configuración de la empresa, los 9 servicios y los clientes (`apps/web/fixtures/contenido_inicial.json`). Se corre una sola vez: volver a correrlo pisa lo editado desde el admin.
- `createsuperuser` crea la única cuenta con acceso a `/admin/`. No hay otras cuentas ni autorregistro.
- Después se entra a `/admin/`, se completan los datos de la empresa y se suben las fotos y los logos.

## 7. Pendientes
Los pendientes abiertos de despliegue (y de los demás planes) se listan con:

```bash
py -3 .claude/hooks/pendientes.py
```

## Historia: Config as Code (hasta 2026-11)
Diagnóstico del 2026-11-17, con la CLI 5.74.1.

- Hasta este plan la configuración estaba en `railway.json` (Config as Code, que Railway deja de leer el 2026-12-01). El `preDeployCommand` no corrió ni en el despliegue del 2026-10-18 (array de dos comandos) ni en el del 2026-11-17 (una sola cadena); en ambos el sitio dio 500 hasta migrar a mano por `railway ssh`.
- Evidencia: `railway config migrate status` respondió literalmente `✓ No services in production read Config as Code.`. El servicio `web` se creó el 2026-10-18 sin ruta de Config File. El build igual tomó `buildCommand` y `startCommand` del archivo (el log de Railpack 0.43.0 muestra `$ python manage.py collectstatic --noinput` y `$ gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 2 --timeout 60`, con la advertencia de deprecación), pero el `serviceManifest` del despliegue activo `7d40e0af` (commit 0e971fc) traía `"preDeployCommand": null`, `"restartPolicyMaxRetries": 10` (el archivo decía 3) y `"fileServiceManifest": {}`: la sección `deploy` nunca se aplicó.
- Ensayo en seco: la salida de `railway config migrate --variables=unmanaged` desmontaba el volumen (`volumeAttachments.web-media.mountPath ("/data" → null)`, "1 destructive change"); declarando `volume("web-media", { region: "us-east4-eqdc4a", sizeMB: 50000 })` montado en `/data` el plan quedó en `Plan: 0 to add, 2 to change, 0 to destroy`.
