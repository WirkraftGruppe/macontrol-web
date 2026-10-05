"""Serializers de la API de Visitas: alta desde la app y listados del empleado."""

import json
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import serializers

from .models import ProductoAplicado, Visita
from .planillas import MAX_LARGO_TEXTO
from .services import MAX_FOTOS, MAX_PRODUCTOS

MAX_BYTES_FOTO = 8 * 1024 * 1024
MAX_CARACTERES_JSON = 50_000


def validar_tamano_foto(archivo):
    """Rechaza fotos de más de 8 MB."""
    if archivo.size > MAX_BYTES_FOTO:
        raise serializers.ValidationError("Cada foto puede pesar hasta 8 MB.")


class CampoJSON(serializers.CharField):
    """Texto JSON dentro de un multipart; entrega el valor ya decodificado."""

    default_error_messages = {
        "json": "Debe ser un JSON válido.",
        "tipo": "Debe ser un JSON de tipo {tipo}.",
    }

    def __init__(self, *, tipo, nombre_tipo, **kwargs):
        kwargs.setdefault("max_length", MAX_CARACTERES_JSON)
        super().__init__(**kwargs)
        self.tipo, self.nombre_tipo = tipo, nombre_tipo

    def to_internal_value(self, data):
        texto = super().to_internal_value(data)
        try:
            valor = json.loads(texto)
        except (ValueError, RecursionError):
            self.fail("json")
        if not isinstance(valor, self.tipo):
            self.fail("tipo", tipo=self.nombre_tipo)
        return valor


class CrearVisitaSerializer(serializers.Serializer):
    """Forma y límites del alta; las reglas de negocio las aplica el servicio."""

    qr_codigo = serializers.UUIDField()
    proyecto = serializers.IntegerField()
    cliente_uuid = serializers.UUIDField(allow_null=False)
    realizada_en = serializers.DateTimeField()
    latitud = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        min_value=Decimal("-90"),
        max_value=Decimal("90"),
    )
    longitud = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        min_value=Decimal("-180"),
        max_value=Decimal("180"),
    )
    precision_m = serializers.DecimalField(
        max_digits=7,
        decimal_places=1,
        min_value=Decimal("0"),
        required=False,
        allow_null=True,
        default=None,
    )
    datos = CampoJSON(tipo=dict, nombre_tipo="objeto", default=dict)
    productos_aplicados = CampoJSON(tipo=list, nombre_tipo="lista", default=list)
    fotos = serializers.ListField(
        child=serializers.FileField(
            allow_empty_file=False, validators=[validar_tamano_foto]
        ),
        min_length=1,
        max_length=MAX_FOTOS,
    )
    observaciones = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=MAX_LARGO_TEXTO
    )
    incidencia = serializers.BooleanField(required=False, default=False)
    incidencia_detalle = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=MAX_LARGO_TEXTO
    )

    def validate(self, attrs):
        """Rechaza el atraso excesivo, salvo en un reintento ya aceptado.

        Si la visita ya existe, se deja pasar para que el servicio responda 409.
        """
        horas = settings.ATRASO_MAXIMO_HORAS
        if attrs["realizada_en"] < timezone.now() - timedelta(hours=horas):
            if not Visita.objects.filter(cliente_uuid=attrs["cliente_uuid"]).exists():
                raise serializers.ValidationError(
                    {
                        "realizada_en": [
                            f"La visita tiene más de {horas} horas de atraso. "
                            "Avise al administrador para que la cargue como manual."
                        ]
                    }
                )
        return attrs

    def validate_productos_aplicados(self, valor):
        if len(valor) > MAX_PRODUCTOS:
            raise serializers.ValidationError(
                f"Se permiten hasta {MAX_PRODUCTOS} productos por visita."
            )
        if not all(isinstance(item, dict) for item in valor):
            raise serializers.ValidationError("Cada producto debe ser un objeto.")
        return valor


class ProyectoResumenSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    titulo = serializers.CharField()


class SitioResumenSerializer(serializers.Serializer):
    """Sitio sin coordenadas, contactos ni notas."""

    nombre = serializers.CharField()
    direccion = serializers.CharField()
    localidad = serializers.CharField()


class VisitaPendienteSerializer(serializers.ModelSerializer):
    proyecto = ProyectoResumenSerializer(read_only=True)
    sitio = SitioResumenSerializer(source="proyecto.sitio", read_only=True)

    class Meta:
        model = Visita
        fields = ["id", "proyecto", "sitio", "programada_para"]
        read_only_fields = fields


class ProductoAplicadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductoAplicado
        fields = ["producto", "lote", "dosis", "unidad", "cantidad"]
        read_only_fields = fields


class VisitaRealizadaSerializer(serializers.ModelSerializer):
    """Visita realizada para la respuesta del alta y el historial (sin coordenadas)."""

    proyecto = ProyectoResumenSerializer(read_only=True)
    sitio = SitioResumenSerializer(source="proyecto.sitio", read_only=True)
    productos = ProductoAplicadoSerializer(many=True, read_only=True)
    fotos = serializers.SerializerMethodField()

    class Meta:
        model = Visita
        fields = [
            "id",
            "proyecto",
            "sitio",
            "realizada_en",
            "cliente_uuid",
            "datos",
            "observaciones",
            "incidencia",
            "incidencia_detalle",
            "productos",
            "fotos",
        ]
        read_only_fields = fields

    def get_fotos(self, visita) -> list[str]:
        return [
            reverse("api:visitas:foto", args=[foto.codigo])
            for foto in visita.fotos.all()
        ]
