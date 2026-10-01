"""Settings de desarrollo: valores por defecto cómodos, nunca para producción."""

from .base import *  # noqa: F403
from .base import BASE_DIR, env

DEBUG = True

SECRET_KEY = env(
    "SECRET_KEY", default="clave-solo-para-desarrollo-no-usar-en-produccion"
)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
}
