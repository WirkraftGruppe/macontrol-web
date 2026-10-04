"""Serializers de la API de Sitios: respuesta de resolver un QR (solo lectura)."""

from rest_framework import serializers


class SitioQRSerializer(serializers.Serializer):
    """Datos mínimos del sitio; sin coordenadas, contactos, notas ni horario."""

    nombre = serializers.CharField()
    direccion = serializers.CharField()
    localidad = serializers.CharField()


class ClienteQRSerializer(serializers.Serializer):
    razon_social = serializers.CharField()


class TipoServicioQRSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()


class ProyectoQRSerializer(serializers.Serializer):
    """Proyecto activo del sitio con la planilla que debe completar el empleado."""

    id = serializers.IntegerField()
    titulo = serializers.CharField()
    tipo_servicio = TipoServicioQRSerializer()
    esquema_planilla = serializers.ListField(child=serializers.DictField())
    visita_pendiente_propia = serializers.IntegerField(allow_null=True)


class ResolverQRSerializer(serializers.Serializer):
    sitio = SitioQRSerializer()
    cliente = ClienteQRSerializer()
    proyectos = ProyectoQRSerializer(many=True)
