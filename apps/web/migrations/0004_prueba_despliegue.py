"""Migración de prueba sin efecto.

Existe para comprobar en producción que el comando previo de Railway aplica las
migraciones sin intervención manual. No cambia esquema ni datos: el RunPython es noop
en ambos sentidos.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("web", "0003_datos_adjunto_a")]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop),
    ]
