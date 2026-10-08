"""Datos del tablero: contadores y proyectos más urgentes."""

from datetime import timedelta

from django.db.models import Count, Exists, OuterRef, Q
from django.utils import timezone

from apps.proyectos.models import UMBRAL_PROXIMA_DIAS, Proyecto
from apps.visitas.models import Revision, Visita

CANTIDAD_URGENTES = 10


def contadores(hoy=None):
    """Devuelve los contadores del tablero (tres consultas)."""
    hoy = hoy or timezone.localdate()
    limite = hoy + timedelta(days=UMBRAL_PROXIMA_DIAS)
    proyectos = Proyecto.objects.filter(estado=Proyecto.Estado.ACTIVO).aggregate(
        vencidos=Count("pk", filter=Q(proxima_visita__lt=hoy)),
        proximos=Count(
            "pk", filter=Q(proxima_visita__gte=hoy, proxima_visita__lte=limite)
        ),
    )
    visitas = Visita.objects.aggregate(
        pendientes_hoy=Count(
            "pk",
            filter=Q(estado=Visita.Estado.PENDIENTE, programada_para=hoy),
        ),
        incidencias=Count(
            "pk", filter=Q(incidencia=True, incidencia_revisada_en__isnull=True)
        ),
    )
    # Subconsulta: un join con las revisiones multiplicaría las visitas.
    con_incidencia_en_revision = Revision.objects.filter(
        visita=OuterRef("pk"), incidencia_ubicacion=True
    )
    ubicacion = (
        Visita.objects.filter(
            incidencia_revisada_en__isnull=True, cuenta_como_servicio=True
        )
        .filter(Q(incidencia_ubicacion=True) | Exists(con_incidencia_en_revision))
        .count()
    )
    return {**proyectos, **visitas, "incidencias_ubicacion": ubicacion}


def proyectos_urgentes():
    """Los proyectos activos con la próxima visita más temprana."""
    return list(
        Proyecto.objects.filter(
            estado=Proyecto.Estado.ACTIVO, proxima_visita__isnull=False
        )
        .select_related("sitio", "sitio__cliente", "tipo_servicio")
        .order_by("proxima_visita", "pk")[:CANTIDAD_URGENTES]
    )
