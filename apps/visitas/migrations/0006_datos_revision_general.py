from django.db import migrations
from django.db.models import Q


def crear_revisiones_generales(apps, schema_editor):
    """Pasa la evidencia de cada visita realizada a una revisión "General".

    Se escribe a mano porque mueve datos entre tablas, algo que ``makemigrations``
    no genera. Por cada visita con evidencia (o realizada) crea una revisión en el
    punto ``orden=0`` del sitio con las coordenadas, el ``cliente_uuid``, las fechas
    y la planilla; reasigna sus fotos y productos; completa ``abierta_en`` y
    ``cierre``, y deja ``datos`` y ``esquema_planilla`` de la visita vacíos. Una
    visita no realizada con evidencia conserva su revisión pero queda con
    ``incidencia`` marcada: la revisión heredada no sirve para cerrarla.
    """
    Visita = apps.get_model("visitas", "Visita")
    Revision = apps.get_model("visitas", "Revision")
    Foto = apps.get_model("visitas", "Foto")
    ProductoAplicado = apps.get_model("visitas", "ProductoAplicado")
    PuntoControl = apps.get_model("sitios", "PuntoControl")

    candidatas = Visita.objects.filter(
        Q(estado="realizada") | Q(fotos__isnull=False) | Q(productos__isnull=False)
    ).distinct()
    for visita in candidatas.select_related("proyecto"):
        sitio_id = visita.proyecto.sitio_id
        punto = (
            PuntoControl.objects.filter(sitio_id=sitio_id).order_by("orden", "id").first()
        )
        if punto is None:
            punto = PuntoControl.objects.create(
                sitio_id=sitio_id, nombre="General", orden=0
            )
        realizada_en = visita.cerrada_en or visita.creado
        revision = Revision.objects.create(
            visita=visita,
            punto=punto,
            orden=1,
            realizada_en=realizada_en,
            recibida_en=visita.recibida_en or realizada_en,
            cliente_uuid=visita.cliente_uuid,
            latitud=visita.latitud,
            longitud=visita.longitud,
            precision_m=visita.precision_m,
            datos=visita.datos,
            esquema_planilla=visita.esquema_planilla,
        )
        Foto.objects.filter(visita=visita).update(revision=revision)
        ProductoAplicado.objects.filter(visita=visita).update(revision=revision)

        cambios = {
            "datos": {},
            "esquema_planilla": [],
            # El UUID pasó a la revisión: se libera para no duplicar el identificador.
            "cliente_uuid": None,
        }
        if visita.estado == "realizada":
            cambios["abierta_en"] = visita.cerrada_en
            cambios["cierre"] = "empleado" if visita.origen == "app" else "administrador"
        else:
            # La evidencia no se pierde, pero no cuenta para cerrar la visita.
            cambios["incidencia"] = True
            cambios["incidencia_detalle"] = (
                "Evidencia migrada de una visita pendiente (plan puntos-control); revisar."
            )
        Visita.objects.filter(pk=visita.pk).update(**cambios)


def devolver_evidencia_a_visitas(apps, schema_editor):
    """Revierte: la primera revisión de cada visita vuelve a la visita.

    Copia coordenadas, ``cliente_uuid``, ``recibida_en``, planilla, fotos y productos
    de la primera revisión a la visita. Si había varias revisiones, las demás se
    pierden al borrar la tabla: solo la revisión "General" migrada es reversible sin
    pérdida. La marca de incidencia de las visitas no realizadas se deja, porque no
    se distingue de una incidencia cargada a mano.
    """
    Visita = apps.get_model("visitas", "Visita")
    Revision = apps.get_model("visitas", "Revision")
    Foto = apps.get_model("visitas", "Foto")
    ProductoAplicado = apps.get_model("visitas", "ProductoAplicado")

    vistas = set()
    for revision in Revision.objects.order_by("visita_id", "orden", "id"):
        Foto.objects.filter(revision=revision).update(visita_id=revision.visita_id)
        ProductoAplicado.objects.filter(revision=revision).update(
            visita_id=revision.visita_id
        )
        if revision.visita_id in vistas:
            continue
        vistas.add(revision.visita_id)
        Visita.objects.filter(pk=revision.visita_id).update(
            latitud=revision.latitud,
            longitud=revision.longitud,
            precision_m=revision.precision_m,
            cliente_uuid=revision.cliente_uuid,
            recibida_en=revision.recibida_en,
            datos=revision.datos,
            esquema_planilla=revision.esquema_planilla,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("visitas", "0005_revision_y_jornada"),
    ]

    operations = [
        migrations.RunPython(crear_revisiones_generales, devolver_evidencia_a_visitas),
    ]
