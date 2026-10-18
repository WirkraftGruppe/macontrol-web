"""Filtro de logging que oculta datos personales y sensibles."""

import logging
import re
import unicodedata
from collections.abc import Mapping

from django.db.models import Model

# Segmentos que, presentes en el nombre de una clave, marcan su valor como sensible.
FRAGMENTOS_SENSIBLES = (
    "password",
    "contrasena",
    "token",
    "access",
    "refresh",
    "secret",
    "authorization",
    "cuit",
    "latitud",
    "longitud",
    "telefono",
    "contacto",
    "cookie",
    "session",
    "sessionid",
    "csrftoken",
    "csrfmiddlewaretoken",
    "correo",
    "email",
)
OCULTO = "[oculto]"
# Detalle de IntegrityError de PostgreSQL: "Key (cuit)=(2012…) already exists".
_CLAVE_VALOR_DB = re.compile(r"Key \(([^)]*)\)=\(.*?\)(?= |$|\.)")
# Detalle de NOT NULL o CHECK de PostgreSQL: "Failing row contains (…)", la fila entera.
# Cubre hasta el fin del mensaje de esa excepción: un valor puede tener saltos de línea.
_FILA_DB = re.compile(
    r"Failing row contains \(.*?(?=\n\n(?:The above exception|During handling)|\Z)",
    re.DOTALL,
)
PROFUNDIDAD_MAXIMA = 5
_ESTANDAR = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {
    "message",
    "asctime",
}


def _segmentos(clave):
    """Segmentos en minúscula y sin tildes ("Teléfono_x" -> telefono, x)."""
    clave = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", clave)
    clave = unicodedata.normalize("NFKD", clave).casefold()
    clave = "".join(c for c in clave if not unicodedata.combining(c))
    return [s.rstrip("0123456789") or s for s in re.split(r"[^a-z0-9]+", clave) if s]


def _es_sensible(clave):
    return isinstance(clave, str) and any(
        s in FRAGMENTOS_SENSIBLES for s in _segmentos(clave)
    )


def _limpiar(valor, nivel=0):
    """Devuelve una copia sin datos sensibles; más allá del tope oculta todo."""
    if isinstance(valor, Model):
        return f"<{valor._meta.label} pk={valor.pk}>"
    if isinstance(valor, Mapping | list | tuple | set | frozenset):
        if nivel >= PROFUNDIDAD_MAXIMA:
            return OCULTO
        if isinstance(valor, Mapping):
            return {
                k: OCULTO if _es_sensible(k) else _limpiar(v, nivel + 1)
                for k, v in valor.items()
            }
        tipo = next(t for t in (list, tuple, set, frozenset) if isinstance(valor, t))
        return tipo(_limpiar(v, nivel + 1) for v in valor)
    return valor


class FiltroDatosPersonales(logging.Filter):
    """Limpia msg, args y atributos extra del record."""

    def filter(self, record):
        if not isinstance(record.msg, str):
            record.msg = _limpiar(record.msg)
        record.args = _limpiar(record.args)
        if record.exc_info and record.exc_info[0] is not None:
            # Se formatea acá para poder limpiar el traceback antes de emitirlo.
            record.exc_text = logging.Formatter().formatException(record.exc_info)
            record.exc_info = None
        if record.exc_text:
            record.exc_text = _CLAVE_VALOR_DB.sub(
                lambda m: f"Key ({m.group(1)})=({OCULTO})", record.exc_text
            )
            record.exc_text = _FILA_DB.sub(
                f"Failing row contains ({OCULTO}).", record.exc_text
            )
        for clave, valor in list(record.__dict__.items()):
            if clave in _ESTANDAR:
                continue
            setattr(record, clave, OCULTO if _es_sensible(clave) else _limpiar(valor))
        return True
