"""Verificación de ubicación: distancia al punto de una apertura o revisión."""

from math import asin, cos, radians, sin, sqrt

from django.conf import settings

RADIO_TIERRA_M = 6_371_000


def distancia_m(lat1, lng1, lat2, lng2) -> int:
    """Distancia en metros entre dos coordenadas (haversine), redondeada."""
    fi1, fi2 = radians(float(lat1)), radians(float(lat2))
    dfi = fi2 - fi1
    dlng = radians(float(lng2)) - radians(float(lng1))
    a = sin(dfi / 2) ** 2 + cos(fi1) * cos(fi2) * sin(dlng / 2) ** 2
    return round(2 * RADIO_TIERRA_M * asin(sqrt(min(1.0, a))))


def _referencia(punto):
    """Coordenadas del punto o, si no las tiene, las del sitio; si no, `None`."""
    for origen in (punto, punto.sitio):
        if origen.latitud is not None and origen.longitud is not None:
            return origen.latitud, origen.longitud
    return None


def verificar(punto, latitud, longitud) -> tuple[int | None, bool]:
    """Devuelve `(distancia_m, incidencia)`; nunca rechaza.

    Sin coordenadas informadas o sin referencia queda "sin verificar": distancia
    nula y sin incidencia. Hay incidencia si la distancia supera `DISTANCIA_MAXIMA_M`.
    """
    referencia = _referencia(punto)
    if latitud is None or longitud is None or referencia is None:
        return None, False
    distancia = distancia_m(latitud, longitud, *referencia)
    return distancia, distancia > settings.DISTANCIA_MAXIMA_M
