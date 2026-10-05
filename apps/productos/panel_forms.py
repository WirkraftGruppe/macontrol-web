"""Formularios del panel de Productos."""

from django import forms

from .models import Producto


class ProductoForm(forms.ModelForm):
    """Alta y edición del producto; `activo` permite retirarlo del catálogo."""

    class Meta:
        model = Producto
        fields = [
            "nombre_comercial",
            "principio_activo",
            "registro",
            "presentacion",
            "unidad_dosis_por_defecto",
            "activo",
        ]
