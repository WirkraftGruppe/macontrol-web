from decimal import Decimal

from django.db import migrations


def aplicar_propuestas_pendientes(apps, schema_editor):
    """RunPython justificado: antes de quitar el campo, las propuestas pendientes
    (que ya cumplían la precisión exigida) fijan lat/lng si el punto no las tiene."""
    PuntoControl = apps.get_model("sitios", "PuntoControl")
    pendientes = PuntoControl.objects.filter(
        ubicacion_propuesta__isnull=False, latitud__isnull=True, longitud__isnull=True
    )
    for punto in pendientes:
        propuesta = punto.ubicacion_propuesta
        if not isinstance(propuesta, dict):
            continue
        try:
            latitud = Decimal(str(propuesta["latitud"]))
            longitud = Decimal(str(propuesta["longitud"]))
        except (KeyError, ArithmeticError):
            continue
        punto.latitud = latitud
        punto.longitud = longitud
        punto.save(update_fields=["latitud", "longitud"])


class Migration(migrations.Migration):
    dependencies = [
        ("sitios", "0006_puntocontrol_foto"),
    ]

    operations = [
        migrations.RunPython(aplicar_propuestas_pendientes, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="puntocontrol",
            name="ubicacion_propuesta",
        ),
    ]
