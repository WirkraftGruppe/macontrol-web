"""Servicios de Sitios: supresión de datos, QR y ubicación de los puntos."""

import uuid
from decimal import Decimal

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


def fijar_ubicacion(punto, latitud, longitud):
    """Fija lat/lng del punto (clic en el mapa) y deja el motivo en el historial."""
    punto.latitud = latitud
    punto.longitud = longitud
    punto._change_reason = "Ubicación fijada en el mapa"
    punto.save(update_fields=["latitud", "longitud"])


def aceptar_ubicacion_propuesta(punto):
    """Pasa la ``ubicacion_propuesta`` a lat/lng; falla si no hay propuesta."""
    propuesta = punto.ubicacion_propuesta
    if not propuesta:
        raise ValidationError("El punto no tiene una ubicación propuesta.")
    punto.latitud = Decimal(propuesta["latitud"])
    punto.longitud = Decimal(propuesta["longitud"])
    punto.ubicacion_propuesta = None
    punto._change_reason = "Ubicación propuesta aceptada"
    punto.save(update_fields=["latitud", "longitud", "ubicacion_propuesta"])


def descartar_ubicacion_propuesta(punto):
    """Descarta la propuesta; así una revisión posterior puede traer otra."""
    punto.ubicacion_propuesta = None
    punto._change_reason = "Ubicación propuesta descartada"
    punto.save(update_fields=["ubicacion_propuesta"])


def mover_en_plano(punto, x, y):
    """Guarda la posición del marcador en el plano (fracción 0 a 1)."""
    punto.x = x
    punto.y = y
    punto._change_reason = "Marcador movido en el plano"
    punto.save(update_fields=["x", "y"])


def desactivar_punto(punto):
    """Da de baja el punto: conserva sus revisiones, pero deja de pedirse."""
    punto.activo = False
    punto._change_reason = "Punto desactivado"
    punto.save(update_fields=["activo"])
