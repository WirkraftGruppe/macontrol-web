"""Formularios del panel de Servicios: editor de campos de la planilla."""

from django import forms

from apps.visitas.models import Visita

from .models import CampoPlanilla


def clave_en_uso(tipo_servicio, clave) -> bool:
    """Indica si alguna visita del servicio guardó datos con esa clave."""
    return Visita.objects.filter(
        proyecto__tipo_servicio=tipo_servicio, datos__has_key=clave
    ).exists()


class CampoPlanillaForm(forms.ModelForm):
    """Alta y edición de un campo; `clave` y `tipo` se fijan si ya hay datos."""

    opciones = forms.CharField(
        label="Opciones",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Una opción por línea. Solo para tipos de opción.",
    )

    class Meta:
        model = CampoPlanilla
        fields = [
            "orden",
            "etiqueta",
            "clave",
            "tipo",
            "opciones",
            "obligatorio",
            "ayuda",
        ]

    def __init__(self, *args, tipo_servicio, **kwargs):
        super().__init__(*args, **kwargs)
        self.tipo_servicio = tipo_servicio
        if self.instance.pk:
            self.initial["opciones"] = "\n".join(self.instance.opciones)
            if clave_en_uso(tipo_servicio, self.instance.clave):
                for nombre in ("clave", "tipo"):
                    self.fields[nombre].disabled = True
                    self.fields[
                        nombre
                    ].help_text = "Fijo: hay visitas con datos de este campo."

    def clean_opciones(self):
        lineas = self.cleaned_data["opciones"].splitlines()
        return [linea.strip() for linea in lineas if linea.strip()]

    def clean_clave(self):
        clave = self.cleaned_data["clave"]
        otros = CampoPlanilla.objects.filter(
            tipo_servicio=self.tipo_servicio, clave=clave
        ).exclude(pk=self.instance.pk)
        if otros.exists():
            raise forms.ValidationError("Ya existe un campo con esa clave.")
        return clave

    def clean(self):
        datos = super().clean()
        tipo = datos.get("tipo")
        if tipo in (
            CampoPlanilla.Tipo.OPCION,
            CampoPlanilla.Tipo.OPCION_MULTIPLE,
        ) and not datos.get("opciones"):
            self.add_error("opciones", "Indique al menos una opción.")
        return datos

    def save(self, commit=True):
        self.instance.tipo_servicio = self.tipo_servicio
        return super().save(commit=commit)
