"""Settings compartidos por todos los entornos. Las variables salen del entorno."""

from datetime import timedelta
from pathlib import Path

import environ
from csp.constants import NONCE, NONE, SELF

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Solo se lee del entorno del proceso; no se carga ningún archivo .env.
env = environ.Env()

INSTALLED_APPS = [
    "config.apps.AdminMAControlConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "csp",
    "simple_history",
    "apps.accounts",
    "apps.clientes",
    "apps.sitios",
    "apps.servicios",
    "apps.proyectos",
    "apps.visitas",
    "apps.productos",
    "apps.informes",
    "apps.panel",
    "apps.api",
    "apps.web",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]

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

AUTH_USER_MODEL = "accounts.User"

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

LOGIN_URL = "/panel/ingresar/"
LOGIN_REDIRECT_URL = "/panel/"
LOGOUT_REDIRECT_URL = "/panel/ingresar/"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication"
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_THROTTLE_RATES": {"autenticacion": "10/min"},
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "CHECK_REVOKE_TOKEN": True,
}

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
}
