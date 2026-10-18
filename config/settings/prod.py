"""Settings de producción: variables clave sin default (ver docs/despliegue.md)."""

from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import MIDDLEWARE, env, leer_num_proxies

DEBUG = False

SECRET_KEY = env("SECRET_KEY")

# Recortados y sin vacíos: un host con espacios nunca coincide con el Host pedido.
ALLOWED_HOSTS = [h.strip() for h in env.list("ALLOWED_HOSTS", default=[]) if h.strip()]

if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS está vacío con DJANGO_ENV=production: definí al menos un "
        "host (separados por comas) o toda petición daría 400."
    )

# Orígenes https que Django acepta en los POST (el dominio público del hosting).
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in env.list("CSRF_TRUSTED_ORIGINS", default=[]) if o.strip()
]


def _origen_valido(origen):
    """Solo `https://host[:puerto]`: sin comodines, ruta, consulta ni fragmento."""
    partes = urlsplit(origen)
    return (
        partes.scheme == "https"
        and bool(partes.netloc)
        and "*" not in origen
        and partes.path == ""
        and not partes.query
        and not partes.fragment
    )


_origenes_malos = [o for o in CSRF_TRUSTED_ORIGINS if not _origen_valido(o)]
if _origenes_malos:
    raise ImproperlyConfigured(
        "CSRF_TRUSTED_ORIGINS tiene orígenes inválidos "
        f"({', '.join(_origenes_malos)}): cada uno debe ser https://host, "
        "sin '*' ni ruta."
    )

# Sin default: con un valor de más o de menos, todas las peticiones compartirían IP
# (o el cliente elegiría la suya) y el límite de intentos del login no serviría.
if not env.str("NUM_PROXIES", default="").strip():
    raise ImproperlyConfigured(
        "NUM_PROXIES es obligatoria con DJANGO_ENV=production (entero >= 0)."
    )
NUM_PROXIES = leer_num_proxies()

# Origen público, obligatorio y https: arma el canonical, Open Graph y el sitemap.
SITE_URL = env.str("SITE_URL", default="").strip().rstrip("/")
if not SITE_URL.startswith("https://") or len(SITE_URL) <= len("https://"):
    raise ImproperlyConfigured(
        "SITE_URL es obligatoria con DJANGO_ENV=production y debe empezar con https://."
    )

# WhiteNoise sirve los estáticos de collectstatic, justo después de SecurityMiddleware.
MIDDLEWARE = list(MIDDLEWARE)
MIDDLEWARE.insert(
    MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,
    "whitenoise.middleware.WhiteNoiseMiddleware",
)

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

DATABASES = {"default": env.db("DATABASE_URL")}

# Caché compartida entre los workers de gunicorn (los contadores del login del admin
# viven acá). La tabla se crea con `createcachetable` en el preDeployCommand.
# MAX_ENTRIES alto: con el default (300) el cull de DatabaseCache borraría un tercio
# de las filas y un atacante con muchas IP podría borrar contadores activos.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "cache_sitio",
        "OPTIONS": {"MAX_ENTRIES": 100_000},
    }
}

# HTTPS detrás del proxy del hosting
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# HSTS reversible: se suben después de verificar los subdominios de la empresa
# (ver docs/decisiones.md, "HSTS reversible").
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
