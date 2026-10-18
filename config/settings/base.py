"""Settings compartidos por todos los entornos. Las variables salen del entorno."""

import re
from pathlib import Path

import environ
from csp.constants import NONCE, NONE, SELF
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Solo se lee del entorno del proceso; no se carga ningún archivo .env.
env = environ.Env()


def leer_num_proxies():
    """Cantidad de proxies inversos de confianza (entero >= 0; default 0)."""
    crudo = env("NUM_PROXIES", default="0")
    # Solo dígitos ASCII: int() aceptaría también "٣", "1_0" o " 2 ".
    if not re.fullmatch(r"[0-9]+", crudo):
        raise ImproperlyConfigured("NUM_PROXIES debe ser un entero mayor o igual a 0.")
    return int(crudo)


# Proxies inversos de confianza delante de Django; define la IP real del cliente.
NUM_PROXIES = leer_num_proxies()

# Cabecera de request.META con la IP del cliente que fija el borde del hosting
# (en Railway, HTTP_X_REAL_IP); con valor tiene prioridad sobre NUM_PROXIES.
# Vacía: se usa NUM_PROXIES. Ver config/red.py.
IP_CLIENTE_CABECERA = env.str("IP_CLIENTE_CABECERA", default="")

# Cupos del login del admin: solo cuentan los intentos fallidos.
INTENTOS_FALLIDOS_POR_IP = 20  # fallos por IP dentro de la ventana
VENTANA_MINUTOS = 15  # ventana de los cupos por IP y por (usuario, IP)
FALLOS_POR_USUARIO_E_IP = 5  # fallos por par (usuario, IP) dentro de la ventana
FALLOS_POR_USUARIO = 50  # fallos globales por usuario, desde cualquier IP
VENTANA_USUARIO_MINUTOS = 60  # ventana del cupo global por usuario


INSTALLED_APPS = [
    "config.apps.AdminMAControlConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "csp",
    "apps.web",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "config.limite_cuerpo.LimiteCuerpoMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "config.csp.CSPMiddlewareOrdenado",
]

# Tope del cuerpo de una petición, que revisa LimiteCuerpoMiddleware antes del CSRF.
LIMITE_CUERPO_BYTES = 3 * 1024 * 1024

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation."
        "UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-ar"
TIME_ZONE = "America/Argentina/Buenos_Aires"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "media"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/admin/login/"
LOGIN_REDIRECT_URL = "/admin/"

# Origen público del sitio; arma las URL absolutas del canonical, Open Graph y sitemap.
# Un `SITE_URL=` vacío (como en `.env.example`) también cae al valor por defecto: una
# URL relativa no sirve para el canonical ni para el sitemap.
SITE_URL = env("SITE_URL", default="") or "https://macontrol.com.ar"
SITE_URL = SITE_URL.rstrip("/")
LOGOUT_REDIRECT_URL = "/admin/login/"

# Explícito aunque coincide con el valor por defecto de Django: la cookie de sesión
# no viaja en las peticiones POST entre sitios.
SESSION_COOKIE_SAMESITE = "Lax"

# Hacia otros orígenes solo viaja el origen; con `same-origin` (el valor por defecto
# de Django) no viajaría ni eso.
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Tope de archivos por petición (los formularios del admin suben pocos).
DATA_UPLOAD_MAX_NUMBER_FILES = 12

CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": [SELF],
        "style-src": [SELF, NONCE],
        "script-src": [SELF],
        "img-src": [SELF, "data:"],
        "font-src": [SELF],
        "object-src": [NONE],
        "base-uri": [SELF],
        "frame-ancestors": [NONE],
        "form-action": [SELF],
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "datos_personales": {"()": "config.registro.FiltroDatosPersonales"},
    },
    "handlers": {
        "consola": {
            "class": "logging.StreamHandler",
            "filters": ["datos_personales"],
        },
    },
    "root": {"handlers": ["consola"], "level": "INFO"},
    # Sin los handlers por defecto de Django (sin filtro, con mail_admins).
    "loggers": {
        "django": {"handlers": ["consola"], "level": "INFO", "propagate": False},
        "django.server": {
            "handlers": ["consola"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
