from decimal import Decimal
from math import asin, cos, radians, sin, sqrt

from django.conf import settings
from django.db import migrations
from django.utils import timezone

RADIO_TIERRA_M = 6_371_000


def _distancia_m(lat1, lng1, lat2, lng2):
    """Haversine en metros (copia de ``apps/visitas/ubicacion.py``: una migración
    no importa código de la app, que puede cambiar)."""
    fi1, fi2 = radians(float(lat1)), radians(float(lat2))
    dlng = radians(float(lng2)) - radians(float(lng1))
    a = sin((fi2 - fi1) / 2) ** 2 + cos(fi1) * cos(fi2) * sin(dlng / 2) ** 2
    return round(2 * RADIO_TIERRA_M * asin(sqrt(min(1.0, a))))


def _coordenada(valor, limite):
    """Valor finito y dentro de [-limite, limite], o ``None`` si no es confiable."""
    try:
        valor = Decimal(str(valor))
    except ArithmeticError:
        return None
    return valor if valor.is_finite() and abs(valor) <= limite else None


def aplicar_propuestas_pendientes(apps, schema_editor):
    """RunPython justificado: antes de quitar el campo, las propuestas pendientes
    fijan lat/lng si el punto no las tiene, pero solo las confiables: la revisión
    citada existe y es del mismo punto, su precisión es conocida y no supera
    ``PRECISION_MAXIMA_M``, no tiene incidencia de ubicación (si la revisión es
    anterior a ``visitas.0008`` y no guarda la distancia, se calcula contra el sitio
    y no debe superar ``DISTANCIA_MAXIMA_M``) y sus coordenadas son finitas y están
    en rango. Las coordenadas se toman de la revisión, no del JSON. Cada punto aplicado deja una fila en su historial, a nombre
    del empleado de la visita; las demás propuestas se descartan."""
    PuntoControl = apps.get_model("sitios", "PuntoControl")
    Historico = apps.get_model("sitios", "HistoricalPuntoControl")
    Revision = apps.get_model("visitas", "Revision")
    pendientes = PuntoControl.objects.filter(
        ubicacion_propuesta__isnull=False, latitud__isnull=True, longitud__isnull=True
    )
    for punto in pendientes:
        propuesta = punto.ubicacion_propuesta
        if not isinstance(propuesta, dict):
            continue
        try:
            revision = (
                Revision.objects.select_related("visita")
                .filter(pk=propuesta.get("revision"), punto_id=punto.pk)
                .first()
            )
        except (TypeError, ValueError):
            continue
        if revision is None or revision.incidencia_ubicacion:
            continue
        if (
            revision.precision_m is None
            or revision.precision_m > settings.PRECISION_MAXIMA_M
        ):
            continue
        latitud = _coordenada(revision.latitud, 90)
        longitud = _coordenada(revision.longitud, 180)
        if latitud is None or longitud is None:
            continue
        sitio = punto.sitio
        if (
            revision.distancia_m is None
            and sitio.latitud is not None
            and sitio.longitud is not None
            and _distancia_m(latitud, longitud, sitio.latitud, sitio.longitud)
            > settings.DISTANCIA_MAXIMA_M
        ):
            continue
        punto.latitud = latitud
        punto.longitud = longitud
        punto.save(update_fields=["latitud", "longitud"])
        campos = {
            campo.attname: getattr(punto, campo.attname)
            for campo in Historico._meta.concrete_fields
            if not campo.name.startswith("history_")
        }
        Historico.objects.create(
            **campos,
            history_type="~",
            history_date=timezone.now(),
            history_change_reason=(
                "Propuesta pendiente aplicada al quitar el campo "
                f"(revisión {revision.pk})"
            ),
            history_user_id=revision.visita.empleado_id,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("sitios", "0006_puntocontrol_foto"),
        ("visitas", "0008_ubicacion_y_administrador"),
    ]

    operations = [
        migrations.RunPython(aplicar_propuestas_pendientes, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="puntocontrol",
            name="ubicacion_propuesta",
        ),
    ]
