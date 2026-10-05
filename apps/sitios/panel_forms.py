"""Formularios del panel de Sitios."""

from django import forms

from .models import Sitio


class SitioForm(forms.ModelForm):
    """Alta y edición de un sitio; lat y lng se cargan a mano."""

    class Meta:
        model = Sitio
        fields = [
            "cliente",
            "nombre",
            "direccion",
            "localidad",
            "latitud",
            "longitud",
            "sector",
            "contacto_en_sitio",
            "telefono_en_sitio",
            "horario_acceso",
            "notas",
            "activo",
        ]
        widgets = {
            "notas": forms.Textarea(attrs={"rows": 3}),
        }
