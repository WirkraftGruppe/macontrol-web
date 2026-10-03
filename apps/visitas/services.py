from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.proyectos.models import Proyecto
from apps.visitas.models import Visita

TOLERANCIA_FUTURO = timedelta(minutes=10)


def registrar_visita_realizada(visita, empleado, realizada_en):
    """Marca la visita como realizada y actualiza el proyecto; devuelve la copia.

    La instancia recibida no se modifica: todo ocurre sobre una copia bloqueada.
    """
    with transaction.atomic():
        visita_bd = Visita.objects.select_for_update().get(pk=visita.pk)
        proyecto = Proyecto.objects.select_for_update().get(pk=visita_bd.proyecto_id)

        if visita_bd.estado != Visita.Estado.PENDIENTE:
            raise ValidationError("Solo se puede registrar una visita pendiente.")
        if realizada_en > timezone.now() + TOLERANCIA_FUTURO:
            raise ValidationError("La fecha de realización no puede ser futura.")
        if visita_bd.origen == Visita.Origen.APP:
            if visita_bd.latitud is None or visita_bd.longitud is None:
                raise ValidationError("Una visita desde la app exige coordenadas.")
            if not visita_bd.fotos.exists():
                raise ValidationError(
                    "Una visita desde la app exige al menos una foto."
                )
        elif visita_bd.origen == Visita.Origen.MANUAL:
            if not (visita_bd.motivo_manual or "").strip():
                raise ValidationError("Una visita manual exige el motivo.")

        visita_bd.empleado = empleado
        visita_bd.estado = Visita.Estado.REALIZADA
        visita_bd.realizada_en = realizada_en
        visita_bd.esquema_planilla = proyecto.tipo_servicio.esquema_planilla()
        visita_bd.full_clean()
        visita_bd.save()

        hay_posterior = (
            Visita.objects.filter(
                proyecto=proyecto,
                estado=Visita.Estado.REALIZADA,
                realizada_en__gt=realizada_en,
            )
            .exclude(pk=visita_bd.pk)
            .exists()
        )
        if not hay_posterior:
            proyecto.encargado_actual = empleado
            if proyecto.frecuencia_dias:
                proyecto.proxima_visita = timezone.localdate(realizada_en) + timedelta(
                    days=proyecto.frecuencia_dias
                )
            proyecto.save(
                update_fields=["encargado_actual", "proxima_visita", "actualizado"]
            )
    return visita_bd
