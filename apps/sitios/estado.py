"""Estado de revisión de un punto de control respecto de los proyectos de su sitio."""

import datetime
from collections import defaultdict

from django.db import models
from django.db.models import Max
from django.utils import timezone

from apps.proyectos.models import UMBRAL_PROXIMA_DIAS, Proyecto
from apps.visitas.models import Revision, Visita


class EstadoPunto(models.TextChoices):
    AL_DIA = "al_dia", "Al día"
    PROXIMA = "proxima", "Próxima"
    VENCIDA = "vencida", "Vencida"
    SIN_REVISAR = "sin_revisar", "Sin revisar"


GRAVEDAD_PUNTO = {
    EstadoPunto.AL_DIA: 0,
    EstadoPunto.PROXIMA: 1,
    EstadoPunto.SIN_REVISAR: 2,
    EstadoPunto.VENCIDA: 3,
}

# Las revisiones de visitas canceladas no cuentan.
_VISITAS_QUE_CUENTAN = [Visita.Estado.ABIERTA, Visita.Estado.REALIZADA]


def peor_estado_punto(estados):
    """Devuelve el más grave de los estados; sin estados, ``al_dia``."""
    return max(estados, key=lambda e: GRAVEDAD_PUNTO[e], default=EstadoPunto.AL_DIA)


def _estado(ultima, frecuencia_dias, hoy):
    """Estado de un punto según su última revisión y la frecuencia del proyecto."""
    if ultima is None:
        return EstadoPunto.SIN_REVISAR
    if not frecuencia_dias:
        return EstadoPunto.AL_DIA
    vence = timezone.localtime(ultima).date() + datetime.timedelta(days=frecuencia_dias)
    if vence < hoy:
        return EstadoPunto.VENCIDA
    if vence <= hoy + datetime.timedelta(days=UMBRAL_PROXIMA_DIAS):
        return EstadoPunto.PROXIMA
    return EstadoPunto.AL_DIA


def estado_revision(punto, proyecto):
    """Estado del punto para un proyecto, a partir de su última revisión."""
    ultima = Revision.objects.filter(
        punto=punto,
        visita__proyecto=proyecto,
        visita__estado__in=_VISITAS_QUE_CUENTAN,
    ).aggregate(ultima=Max("realizada_en"))["ultima"]
    return _estado(ultima, proyecto.frecuencia_dias, timezone.localdate())


def estados_de_puntos(puntos):
    """Estado de cada punto: el peor entre los proyectos activos de su sitio.

    Devuelve ``{id_del_punto: estado}`` con dos consultas, sin importar cuántos
    puntos haya. Un sitio sin proyectos activos queda ``al_dia``.
    """
    puntos = list(puntos)
    if not puntos:
        return {}
    hoy = timezone.localdate()
    proyectos = defaultdict(list)
    for pk, sitio_id, frecuencia in Proyecto.objects.filter(
        sitio_id__in={p.sitio_id for p in puntos}, estado=Proyecto.Estado.ACTIVO
    ).values_list("pk", "sitio_id", "frecuencia_dias"):
        proyectos[sitio_id].append((pk, frecuencia))
    ultimas = {
        (fila["punto_id"], fila["visita__proyecto_id"]): fila["ultima"]
        for fila in Revision.objects.filter(
            punto_id__in=[p.pk for p in puntos],
            visita__proyecto_id__in=[
                pk for lista in proyectos.values() for pk, _ in lista
            ],
            visita__estado__in=_VISITAS_QUE_CUENTAN,
        )
        .values("punto_id", "visita__proyecto_id")
        .annotate(ultima=Max("realizada_en"))
    }
    return {
        punto.pk: peor_estado_punto(
            _estado(ultimas.get((punto.pk, proyecto_id)), frecuencia, hoy)
            for proyecto_id, frecuencia in proyectos[punto.sitio_id]
        )
        for punto in puntos
    }
