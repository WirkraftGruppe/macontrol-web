"""Filtro de logging que oculta datos personales y sensibles."""

import logging

from django.db.models import Model

CLAVES_SENSIBLES = {"password", "token", "latitud", "longitud", "cuit"}
OCULTO = "[oculto]"


def _limpiar_dict(datos):
    return {
        k: OCULTO if k in CLAVES_SENSIBLES else _limpiar_valor(v)
        for k, v in datos.items()
    }


def _limpiar_valor(valor):
    if isinstance(valor, Model):
        return f"<{valor._meta.label} pk={valor.pk}>"
    if isinstance(valor, dict):
        return _limpiar_dict(valor)
    return valor


class FiltroDatosPersonales(logging.Filter):
    """Reemplaza claves sensibles e instancias de modelo en args y extras."""

    def filter(self, record):
        if isinstance(record.args, dict):
            record.args = _limpiar_dict(record.args)
        elif isinstance(record.args, tuple):
            record.args = tuple(_limpiar_valor(a) for a in record.args)
        estandar = logging.LogRecord("", 0, "", 0, "", (), None).__dict__
        for clave in list(record.__dict__):
            if clave in estandar or clave in ("message", "asctime"):
                continue
            if clave in CLAVES_SENSIBLES:
                setattr(record, clave, OCULTO)
            else:
                setattr(record, clave, _limpiar_valor(record.__dict__[clave]))
        return True
