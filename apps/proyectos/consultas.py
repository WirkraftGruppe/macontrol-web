"""Consultas de Proyectos reutilizables por el panel."""

from datetime import timedelta

from django.utils import timezone

from .models import UMBRAL_PROXIMA_DIAS, EstadoVisita


def filtrar_por_estado_visita(queryset, estado):
    """Filtra por la misma regla que `Proyecto.estado_visita`, a nivel de base.

    Un estado desconocido o vacío devuelve el queryset sin filtrar.
    """
    hoy = timezone.localdate()
    limite = hoy + timedelta(days=UMBRAL_PROXIMA_DIAS)
    if estado == EstadoVisita.SIN_PROGRAMAR:
        return queryset.filter(proxima_visita__isnull=True)
    if estado == EstadoVisita.VENCIDA:
        return queryset.filter(proxima_visita__lt=hoy)
    if estado == EstadoVisita.PROXIMA:
        return queryset.filter(proxima_visita__gte=hoy, proxima_visita__lte=limite)
    if estado == EstadoVisita.AL_DIA:
        return queryset.filter(proxima_visita__gt=limite)
    return queryset
