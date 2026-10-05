"""Filtros de interfaz compartidos por las plantillas del panel."""

from django import template

register = template.Library()

TONOS = {
    # Semáforo de proyectos
    "vencida": "danger",
    "proxima": "warn",
    "al_dia": "ok",
    "sin_programar": "neutral",
    # Estados de visita
    "realizada": "ok",
    "pendiente": "warn",
    "cancelada": "neutral",
}


@register.filter
def tono_estado(valor):
    """Devuelve el tono (ok, warn, danger, neutral) de un estado."""
    return TONOS.get(str(valor), "neutral")
