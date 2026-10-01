"""Elige el módulo de settings según DJANGO_ENV (development | production)."""

import os

from django.core.exceptions import ImproperlyConfigured

_entorno = os.environ.get("DJANGO_ENV", "")

if _entorno == "development":
    from .dev import *  # noqa: F403
elif _entorno == "production":
    from .prod import *  # noqa: F403
else:
    raise ImproperlyConfigured(
        "Definir DJANGO_ENV como 'development' o 'production' "
        f"(valor actual: {_entorno!r})."
    )
