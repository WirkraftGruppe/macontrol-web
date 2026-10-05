"""Vistas de la API de Visitas: pendientes, alta, historial y fotos."""

from django.core.exceptions import (
    RequestDataTooBig,
    TooManyFieldsSent,
    TooManyFilesSent,
)
from django.db.models import F
from django.http import FileResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, serializers, status
from rest_framework.exceptions import APIException, NotFound, PermissionDenied
from rest_framework.negotiation import BaseContentNegotiation
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.permisos import EsAdministrador, EsEmpleado

from .models import Foto, Visita
from .serializers import (
    MAX_BYTES_FOTO,
    MAX_FOTOS,
    CrearVisitaSerializer,
    VisitaPendienteSerializer,
    VisitaRealizadaSerializer,
)
from .services import VisitaDuplicada, registrar_visita_desde_app

MENSAJE_DUPLICADA = "La visita ya fue registrada."
MAX_BYTES_PEDIDO = MAX_FOTOS * MAX_BYTES_FOTO + 1024 * 1024


class PedidoDemasiadoGrande(APIException):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    default_detail = "El pedido supera el tamaño permitido."
    default_code = "pedido_demasiado_grande"


class MisVisitasView(generics.ListAPIView):
    """Visitas pendientes del empleado autenticado."""

    permission_classes = [EsEmpleado]
    serializer_class = VisitaPendienteSerializer

    def get_queryset(self):
        return (
            Visita.objects.filter(
                empleado=self.request.user, estado=Visita.Estado.PENDIENTE
            )
            .select_related("proyecto__sitio")
            .order_by(F("programada_para").asc(nulls_last=True), "id")
        )

    @extend_schema(summary="Mis visitas pendientes")
    def get(self, request, *args, **kwargs):
        """Lista paginada de las pendientes propias."""
        return super().get(request, *args, **kwargs)


class CrearVisitaView(APIView):
    """Registra una visita realizada desde la app (multipart)."""

    permission_classes = [EsEmpleado]
    parser_classes = [MultiPartParser]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "crear_visita"

    @extend_schema(
        summary="Registrar una visita realizada",
        description=(
            "Multipart. `datos` y `productos_aplicados` son texto JSON; `fotos` se "
            "repite de 1 a 10 veces (hasta 8 MB cada una). Un `cliente_uuid` ya "
            "registrado responde 409; `visita` solo viene si es del mismo empleado."
        ),
        request={"multipart/form-data": CrearVisitaSerializer},
        responses={
            201: VisitaRealizadaSerializer,
            409: OpenApiResponse(description="El `cliente_uuid` ya fue registrado."),
        },
    )
    def post(self, request):
        """Valida la forma y delega en el servicio, que maneja su transacción."""
        try:
            largo = int(request.META.get("CONTENT_LENGTH") or 0)
        except ValueError:
            largo = 0
        # Se corta antes de leer el cuerpo: Django escribe los archivos a disco.
        if largo > MAX_BYTES_PEDIDO:
            raise PedidoDemasiadoGrande()
        try:
            datos_pedido = request.data
        except (RequestDataTooBig, TooManyFieldsSent, TooManyFilesSent):
            raise PedidoDemasiadoGrande()
        entrada = CrearVisitaSerializer(data=datos_pedido)
        entrada.is_valid(raise_exception=True)
        try:
            visita = registrar_visita_desde_app(
                empleado=request.user, **entrada.validated_data
            )
        except VisitaDuplicada as duplicada:
            cuerpo = {"detalle": MENSAJE_DUPLICADA, "campos": {}}
            if duplicada.visita.empleado_id == request.user.id:
                cuerpo["visita"] = duplicada.visita.id
            return Response(cuerpo, status=status.HTTP_409_CONFLICT)
        return Response(
            VisitaRealizadaSerializer(visita).data, status=status.HTTP_201_CREATED
        )


class ParametrosHistorialSerializer(serializers.Serializer):
    desde = serializers.DateField(required=False)
    hasta = serializers.DateField(required=False)


class HistorialView(generics.ListAPIView):
    """Visitas realizadas del empleado, con filtro por fecha local."""

    permission_classes = [EsEmpleado]
    serializer_class = VisitaRealizadaSerializer

    def get_queryset(self):
        filtros = ParametrosHistorialSerializer(data=self.request.query_params)
        filtros.is_valid(raise_exception=True)
        fechas = filtros.validated_data
        consulta = Visita.objects.filter(
            empleado=self.request.user, estado=Visita.Estado.REALIZADA
        )
        if "desde" in fechas:
            consulta = consulta.filter(cerrada_en__date__gte=fechas["desde"])
        if "hasta" in fechas:
            consulta = consulta.filter(cerrada_en__date__lte=fechas["hasta"])
        return (
            consulta.select_related("proyecto__sitio")
            .prefetch_related("revisiones__fotos", "revisiones__productos")
            .order_by("-cerrada_en", "-id")
        )

    @extend_schema(
        summary="Mi historial de visitas realizadas",
        parameters=[
            OpenApiParameter("desde", OpenApiTypes.DATE, description="AAAA-MM-DD"),
            OpenApiParameter("hasta", OpenApiTypes.DATE, description="AAAA-MM-DD"),
        ],
    )
    def get(self, request, *args, **kwargs):
        """Lista paginada; `desde` y `hasta` son inclusivos (fecha local)."""
        return super().get(request, *args, **kwargs)


class IgnorarAccept(BaseContentNegotiation):
    """Usa siempre el primer renderer: la imagen no depende del `Accept`."""

    def select_parser(self, request, parsers):
        return parsers[0] if parsers else None

    def select_renderer(self, request, renderers, format_suffix=None):
        return renderers[0], renderers[0].media_type


class FotoView(APIView):
    """Sirve la foto a su empleado o a un administrador."""

    permission_classes = [EsEmpleado | EsAdministrador]
    content_negotiation_class = IgnorarAccept

    @extend_schema(
        summary="Descargar una foto",
        responses={
            (200, "image/jpeg"): OpenApiTypes.BINARY,
            403: OpenApiResponse(description="La foto es de otro empleado."),
            404: OpenApiResponse(description="La foto no existe."),
        },
    )
    def get(self, request, codigo):
        """Devuelve el JPEG; 404 si no existe y 403 si no corresponde."""
        foto = (
            Foto.objects.select_related("revision__visita")
            .filter(codigo=codigo)
            .first()
        )
        if foto is None:
            raise NotFound("La foto no existe.")
        if not (
            request.user.es_administrador
            or foto.revision.visita.empleado_id == request.user.id
        ):
            raise PermissionDenied("No tiene acceso a esta foto.")
        try:
            archivo = foto.imagen.open("rb")
        except FileNotFoundError:
            raise NotFound("La foto no existe.")
        respuesta = FileResponse(archivo, content_type="image/jpeg")
        respuesta["Cache-Control"] = "private, no-store"
        respuesta["X-Content-Type-Options"] = "nosniff"
        return respuesta
