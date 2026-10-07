import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

MOTIVO_ESCANEO = "Ubicación fijada por el primer escaneo"


def llenar_ubicacion_fijada(apps, schema_editor):
    """RunPython justificado: el historial ya dice quién y cuándo fijó la ubicación
    de cada punto por el primer escaneo; se copia a los campos nuevos para que el
    panel no tenga que recorrer el historial. De cada punto manda la fila más
    reciente con ese motivo; los demás puntos quedan sin dato."""
    Punto = apps.get_model("sitios", "PuntoControl")
    Historico = apps.get_model("sitios", "HistoricalPuntoControl")
    vistos = set()
    filas = Historico.objects.filter(history_change_reason=MOTIVO_ESCANEO).order_by(
        "-history_date", "-history_id"
    )
    for fila in filas:
        if fila.id in vistos:
            continue
        vistos.add(fila.id)
        Punto.objects.filter(pk=fila.id).update(
            ubicacion_fijada_por_id=fila.history_user_id,
            ubicacion_fijada_en=fila.history_date,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("sitios", "0007_quitar_ubicacion_propuesta"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalpuntocontrol",
            name="ubicacion_fijada_en",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="ubicación fijada en"
            ),
        ),
        migrations.AddField(
            model_name="historicalpuntocontrol",
            name="ubicacion_fijada_por",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
                verbose_name="ubicación fijada por",
            ),
        ),
        migrations.AddField(
            model_name="puntocontrol",
            name="precision_m",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=7,
                null=True,
                verbose_name="precisión del GPS (m)",
            ),
        ),
        migrations.AddField(
            model_name="puntocontrol",
            name="ubicacion_fijada_en",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="ubicación fijada en"
            ),
        ),
        migrations.AddField(
            model_name="puntocontrol",
            name="ubicacion_fijada_por",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
                verbose_name="ubicación fijada por",
            ),
        ),
        migrations.AddField(
            model_name="sitio",
            name="precision_m",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=7,
                null=True,
                verbose_name="precisión del GPS (m)",
            ),
        ),
        migrations.RunPython(llenar_ubicacion_fijada, migrations.RunPython.noop),
    ]
