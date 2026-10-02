"""Servicios de Sitios: supresión de datos y regeneración del código QR."""

import uuid

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import ProtectedError

from .models import Sitio

TOPE_REGENERAR_QR = 20


def suprimir_sitio(sitio):
    """Suprime el sitio y todo su historial (supresión de datos personales, Ley 25.326).

    Si el sitio tiene proyectos, ``ProtectedError`` se propaga y no se borra nada.
    """
    with transaction.atomic():
        pk = sitio.pk
        sitio.delete()
        Sitio.history.filter(id=pk).delete()


def suprimir_sitios(sitios):
    """Suprime cada sitio por separado.

    Devuelve ``(suprimidos, con_proyectos)``: la cantidad suprimida y la lista de
    sitios que no se pudieron suprimir por tener proyectos.
    """
    suprimidos = 0
    con_proyectos = []
    for sitio in sitios:
        try:
            suprimir_sitio(sitio)
        except ProtectedError:
            con_proyectos.append(sitio)
        else:
            suprimidos += 1
    return suprimidos, con_proyectos


def regenerar_qr(sitio):
    """Genera un nuevo ``qr_codigo`` (invalida la etiqueta impresa).

    Deja el motivo en el historial.
    """
    sitio.qr_codigo = uuid.uuid4()
    sitio.qr_impreso_el = None
    sitio._change_reason = "Regeneración de QR"
    sitio.save(update_fields=["qr_codigo", "qr_impreso_el", "actualizado"])
    return sitio.qr_codigo


def regenerar_qr_lote(sitios):
    """Regenera el QR de varios sitios; rechaza el lote si supera ``TOPE_REGENERAR_QR``.

    Devuelve la cantidad de sitios regenerados.
    """
    if len(sitios) > TOPE_REGENERAR_QR:
        raise ValidationError(
            f"No se pueden regenerar más de {TOPE_REGENERAR_QR} códigos QR a la vez "
            f"(se seleccionaron {len(sitios)})."
        )
    for sitio in sitios:
        regenerar_qr(sitio)
    return len(sitios)
