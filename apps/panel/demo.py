"""Guardas compartidas por los comandos de demostración."""

import os

from django.conf import settings
from django.core.management.base import CommandError
from django.db import connection


def _es_sqlite(config):
    """True solo si la base es SQLite: un HOST local puede ser un túnel a producción."""
    return config.get("ENGINE", "").endswith("sqlite3")


def exigir_entorno_demo(comando="cargar_demo"):
    """Lanza `CommandError` si el entorno no es de desarrollo local con SQLite.

    Exige DEBUG activo, `DJANGO_ENV=development` y SQLite, para que un comando de
    demostración nunca toque una base remota.
    """
    if not settings.DEBUG:
        raise CommandError(f"{comando} solo se puede ejecutar con DEBUG activo.")
    if os.environ.get("DJANGO_ENV") != "development":
        raise CommandError(f"{comando} exige DJANGO_ENV=development.")
    if not _es_sqlite(connection.settings_dict):
        raise CommandError(
            f"{comando} solo corre contra SQLite (DJANGO_ENV=development sin "
            "DATABASE_URL)."
        )
