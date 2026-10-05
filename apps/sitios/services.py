"""Servicios de Sitios: supresión de datos y regeneración del QR de un punto."""

import uuid

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import ProtectedError

from apps.proyectos.models import Proyecto

from .models import Plano, PuntoControl, Sitio

TOPE_REGENERAR_QR = 20


def suprimir_sitio(sitio):
    """Suprime el sitio y su historial, y el de sus proyectos (Ley 25.326).

    Si el sitio tiene proyectos, ``ProtectedError`` se propaga y no se borra nada.
    """
    with transaction.atomic():
        pk = sitio.pk
        sitio.delete()
        Sitio.history.filter(id=pk).delete()
        Proyecto.history.filter(sitio_id=pk).delete()
        PuntoControl.history.filter(sitio_id=pk).delete()
        Plano.history.filter(sitio_id=pk).delete()


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


def regenerar_qr(punto):
    """Genera un nuevo ``qr_codigo`` del punto (invalida la etiqueta impresa).

    Deja el motivo en el historial.
    """
    punto.qr_codigo = uuid.uuid4()
    punto.qr_impreso_el = None
    punto._change_reason = "Regeneración de QR"
    punto.save(update_fields=["qr_codigo", "qr_impreso_el"])
    return punto.qr_codigo


def regenerar_qr_lote(puntos):
    """Regenera el QR de varios puntos; rechaza el lote si supera ``TOPE_REGENERAR_QR``.

    Devuelve la cantidad de puntos regenerados.
    """
    if len(puntos) > TOPE_REGENERAR_QR:
        raise ValidationError(
            f"No se pueden regenerar más de {TOPE_REGENERAR_QR} códigos QR a la vez "
            f"(se seleccionaron {len(puntos)})."
        )
    with transaction.atomic():
        for punto in puntos:
            regenerar_qr(punto)
    return len(puntos)
