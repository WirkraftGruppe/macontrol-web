"""Serializers de Productos para la API."""

from rest_framework import serializers

from .models import Producto


class ProductoSerializer(serializers.ModelSerializer):
    """Representación de solo lectura de un producto del catálogo."""

    class Meta:
        model = Producto
        fields = [
            "id",
            "nombre_comercial",
            "principio_activo",
            "registro",
            "presentacion",
            "unidad_dosis_por_defecto",
        ]
        read_only_fields = fields
