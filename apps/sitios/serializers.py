"""Serializers de la API de Sitios: resolver un QR y puntos del empleado."""

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
    """Proyecto activo del sitio con las planillas que debe completar el empleado."""

    id = serializers.IntegerField()
    titulo = serializers.CharField()
    tipo_servicio = TipoServicioQRSerializer()
    esquema_punto = serializers.ListField(child=serializers.DictField())
    esquema_visita = serializers.ListField(child=serializers.DictField())
    visita_pendiente_propia = serializers.IntegerField(allow_null=True)
    visita_abierta_propia = serializers.IntegerField(allow_null=True)


class PuntoPlanoSerializer(serializers.Serializer):
    """Marcador de un punto sobre el plano, con su estado de revisión."""

    id = serializers.IntegerField()
    nombre = serializers.CharField()
    x = serializers.FloatField()
    y = serializers.FloatField()
    estado = serializers.CharField()


class PlanoSerializer(serializers.Serializer):
    """Plano del punto escaneado; `url` apunta al endpoint autenticado de la imagen."""

    id = serializers.IntegerField()
    nombre = serializers.CharField()
    url = serializers.CharField()
    ancho_px = serializers.IntegerField()
    alto_px = serializers.IntegerField()
    puntos = PuntoPlanoSerializer(many=True)


class PuntoQRSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()
    sector = serializers.CharField()
    plano = PlanoSerializer(allow_null=True)


class ResolverQRSerializer(serializers.Serializer):
    punto = PuntoQRSerializer()
    sitio = SitioQRSerializer()
    cliente = ClienteQRSerializer()
    proyectos = ProyectoQRSerializer(many=True)


class SitioPuntoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()


class MiPuntoSerializer(serializers.Serializer):
    """Punto activo de un sitio donde el empleado tiene trabajo, con su estado."""

    id = serializers.IntegerField()
    nombre = serializers.CharField()
    sector = serializers.CharField()
    sitio = SitioPuntoSerializer()
    plano = serializers.IntegerField(source="plano_id", allow_null=True)
    x = serializers.FloatField(allow_null=True)
    y = serializers.FloatField(allow_null=True)
    latitud = serializers.FloatField(allow_null=True)
    longitud = serializers.FloatField(allow_null=True)
    estado = serializers.CharField()


class MisPuntosParametrosSerializer(serializers.Serializer):
    """Parámetros de consulta de `GET me/puntos/`."""

    sitio = serializers.IntegerField(required=False, min_value=1)
