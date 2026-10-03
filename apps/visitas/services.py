from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.visitas.models import Visita


def registrar_visita_realizada(visita, empleado, realizada_en):
    """Marca la visita como realizada y actualiza el proyecto; devuelve la visita."""
    if visita.estado != Visita.Estado.PENDIENTE:
        raise ValidationError("Solo se puede registrar una visita pendiente.")
    if visita.origen == Visita.Origen.APP:
        if visita.latitud is None or visita.longitud is None:
            raise ValidationError("Una visita desde la app exige coordenadas.")
        if not visita.fotos.exists():
            raise ValidationError("Una visita desde la app exige al menos una foto.")
    elif visita.origen == Visita.Origen.MANUAL:
        if not (visita.motivo_manual or "").strip():
            raise ValidationError("Una visita manual exige el motivo.")

    with transaction.atomic():
        proyecto = visita.proyecto
        visita.empleado = empleado
        visita.estado = Visita.Estado.REALIZADA
        visita.realizada_en = realizada_en
        visita.esquema_planilla = proyecto.tipo_servicio.esquema_planilla()
        visita.full_clean()
        visita.save()

        proyecto.encargado_actual = empleado
        if proyecto.frecuencia_dias:
            proyecto.proxima_visita = timezone.localdate(realizada_en) + timedelta(
                days=proyecto.frecuencia_dias
            )
        proyecto.save(
            update_fields=["encargado_actual", "proxima_visita", "actualizado"]
        )
    return visita
