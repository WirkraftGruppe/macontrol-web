"""Settings de desarrollo: valores por defecto cómodos, nunca para producción."""

import ipaddress

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import BASE_DIR, env

DEBUG = True

SECRET_KEY = env(
    "SECRET_KEY", default="clave-solo-para-desarrollo-no-usar-en-produccion"
)

# Recortados y sin vacíos: "localhost, 192.168.1.10" no debe dejar " 192.168.1.10".
ALLOWED_HOSTS = [
    h.strip()
    for h in env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
    if h.strip()
]

_HOSTS_LOCALES = {"localhost", "127.0.0.1", "[::1]", "::1", "testserver"}


def _es_host_local(host):
    """Local, loopback o IP privada (la app móvil prueba por la red local)."""
    if host in _HOSTS_LOCALES:
        return True
    try:
        ip = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback


_hosts_publicos = [h for h in ALLOWED_HOSTS if not _es_host_local(h)]
if _hosts_publicos:
    raise ImproperlyConfigured(
        f"ALLOWED_HOSTS tiene hosts públicos ({', '.join(_hosts_publicos)}) con "
        "DJANGO_ENV=development: para un servidor público hay que "
        "usar DJANGO_ENV=production."
    )

DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
}
