from decimal import Decimal

from django.db import migrations
from django.utils import timezone


def _coordenada(propuesta, clave, limite):
    """Valor finito y dentro de [-limite, limite], o ``None`` si no es confiable."""
    try:
        valor = Decimal(str(propuesta[clave]))
    except (KeyError, ArithmeticError):
        return None
    return valor if valor.is_finite() and abs(valor) <= limite else None


def aplicar_propuestas_pendientes(apps, schema_editor):
    """RunPython justificado: antes de quitar el campo, las propuestas pendientes
    fijan lat/lng si el punto no las tiene, pero solo las confiables: la revisión
    citada existe y no tiene incidencia de ubicación, y las coordenadas son finitas
    y están en rango. Cada punto aplicado deja una fila en su historial, a nombre
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
                .filter(pk=propuesta.get("revision"))
                .first()
            )
        except (TypeError, ValueError):
            continue
        if revision is None or revision.incidencia_ubicacion:
            continue
        latitud = _coordenada(propuesta, "latitud", 90)
        longitud = _coordenada(propuesta, "longitud", 180)
        if latitud is None or longitud is None:
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
