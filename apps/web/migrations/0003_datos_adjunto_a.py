"""Lleva a producción los datos reales de la empresa (Adjunto A, 2026-11-17).

RunPython justificado: el cambio es de datos, no de esquema, y la base de producción
ya tiene cargada la configuración vieja (teléfono, direcciones, habilitación). Solo
actualiza una fila existente; si no hay `Configuracion` no crea nada. Reverso: noop,
porque los valores anteriores no se restauran. No toca `titulo_seo` ni `eslogan`.
"""

from django.db import migrations

CONFIGURACION = {
    "razon_social": "MAControl S.A.",
    "cuit": "30-71834106-6",
    "director_tecnico": "Miguel Canale",
    "direcciones": [
        {
            "localidad": "Castelli",
            "direccion": "Saavedra 555",
            "provincia": "Buenos Aires",
        }
    ],
    "telefono": "02241 15-546232",
    "telefono_internacional": "+5492241546232",
    "telefono_2": "02241 15-496047",
    "telefono_2_internacional": "+5492241496047",
    "whatsapp": "+5492241546232",
    "correo": "administracion@macontrol.com.ar",
    "horario": "Atención las 24 horas, todos los días",
    "atiende_24_horas": True,
    "habilitacion": "Empresa inscripta y habilitada — Ministerio de Desarrollo Agrario",
}

NOMBRES = {
    "mosquitos-vectores": "Control de mosquitos vectores",
    "manejo-plagas-edificios": "Manejo integral de plagas en edificios y departamentos",
    "servicio-mipu": "Servicio MIPU",
}

PREFIJO_MIPU = "Manejo Integral de Plagas Urbanas (MIPU): "


def cargar_adjunto_a(apps, schema_editor):
    Configuracion = apps.get_model("web", "Configuracion")
    Servicio = apps.get_model("web", "Servicio")
    config = Configuracion.objects.filter(pk=1).first()
    if config is not None:
        for campo, valor in CONFIGURACION.items():
            setattr(config, campo, valor)
        config.presentacion = config.presentacion.replace(
            "más de diez años", "15 años"
        )
        config.save()
    for slug, nombre in NOMBRES.items():
        Servicio.objects.filter(slug=slug).update(nombre=nombre)
    mipu = Servicio.objects.filter(slug="servicio-mipu").first()
    if mipu is not None and not mipu.resumen.startswith(PREFIJO_MIPU):
        mipu.resumen = PREFIJO_MIPU + mipu.resumen
        mipu.save(update_fields=["resumen"])


class Migration(migrations.Migration):
    dependencies = [("web", "0002_configuracion_datos_empresa")]

    operations = [migrations.RunPython(cargar_adjunto_a, migrations.RunPython.noop)]
