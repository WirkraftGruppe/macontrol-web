"""Servicios de Sitios: supresión de datos y regeneración del código QR."""

import uuid

from django.db import transaction

from .models import Sitio


def suprimir_sitio(sitio):
    """Suprime el sitio y todo su historial (supresión de datos personales, Ley 25.326).

    Si el sitio tiene proyectos, ``ProtectedError`` se propaga y no se borra nada.
    """
    with transaction.atomic():
        pk = sitio.pk
        sitio.delete()
        Sitio.history.filter(id=pk).delete()


def regenerar_qr(sitio):
    """Genera un nuevo ``qr_codigo``, lo que invalida la etiqueta impresa."""
    sitio.qr_codigo = uuid.uuid4()
    sitio.qr_impreso_el = None
    sitio.save()
    return sitio.qr_codigo
