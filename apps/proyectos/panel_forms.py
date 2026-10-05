"""Formularios del panel de Proyectos."""

from django import forms

from apps.servicios.models import TipoServicio

from .models import Proyecto

CAMPOS_COMUNES = (
    "sitio",
    "tipo_servicio",
    "titulo",
    "detalle",
    "estado",
    "frecuencia_dias",
    "proxima_visita",
)


class FormularioProyectoBase(forms.ModelForm):
    class Meta:
        model = Proyecto
        fields = CAMPOS_COMUNES
        widgets = {"proxima_visita": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo_servicio"].queryset = TipoServicio.objects.filter(activo=True)


class FormularioProyectoAlta(FormularioProyectoBase):
    """El encargado inicial también queda como encargado actual."""

    class Meta(FormularioProyectoBase.Meta):
        fields = (*CAMPOS_COMUNES, "encargado_inicial")

    def save(self, commit=True):
        self.instance.encargado_actual = self.cleaned_data["encargado_inicial"]
        return super().save(commit=commit)


class FormularioProyectoEdicion(FormularioProyectoBase):
    class Meta(FormularioProyectoBase.Meta):
        fields = (*CAMPOS_COMUNES, "encargado_actual")
