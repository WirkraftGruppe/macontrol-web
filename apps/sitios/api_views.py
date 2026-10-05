"""Vistas de la API de Sitios: resolución de códigos QR."""

from django.db.models import F
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.permisos import EsEmpleado
from apps.proyectos.models import Proyecto
from apps.visitas.models import Visita

from .models import PuntoControl
from .serializers import ResolverQRSerializer


class ResolverQRView(APIView):
    """Dado el UUID de un QR, devuelve el sitio y sus proyectos activos."""

    permission_classes = [EsEmpleado]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "qr"

    @extend_schema(
        request=None,
        responses={200: ResolverQRSerializer},
        summary="Resolver un código QR",
        description=(
            "Solo empleados. Un QR inexistente o de un sitio inactivo responde el "
            "mismo 404."
        ),
    )
    def post(self, request, codigo):
        punto = (
            PuntoControl.objects.select_related("sitio__cliente")
            .filter(
                qr_codigo=codigo,
                activo=True,
                sitio__activo=True,
                sitio__cliente__activo=True,
            )
            .first()
        )
        if punto is None:
            raise NotFound("El código QR no corresponde a un sitio activo.")
        sitio = punto.sitio

        proyectos = list(
            Proyecto.objects.filter(sitio=sitio, estado=Proyecto.Estado.ACTIVO)
            .select_related("tipo_servicio")
            .order_by("id")
        )
        # Una sola consulta para las pendientes propias; la más antigua gana.
        pendientes = {}
        visitas = (
            Visita.objects.filter(
                empleado=request.user,
                estado=Visita.Estado.PENDIENTE,
                proyecto__in=proyectos,
            )
            .order_by(F("programada_para").asc(nulls_last=True), "id")
            .values_list("proyecto_id", "id")
        )
        for proyecto_id, visita_id in visitas:
            pendientes.setdefault(proyecto_id, visita_id)

        datos = {
            "sitio": sitio,
            "cliente": sitio.cliente,
            "proyectos": [
                {
                    "id": p.id,
                    "titulo": p.titulo,
                    "tipo_servicio": p.tipo_servicio,
                    "esquema_planilla": p.tipo_servicio.esquema_planilla(),
                    "visita_pendiente_propia": pendientes.get(p.id),
                }
                for p in proyectos
            ],
        }
        return Response(ResolverQRSerializer(datos).data)
