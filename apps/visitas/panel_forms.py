"""Formularios del panel de Visitas."""

from django import forms
from django.utils import timezone

from apps.accounts.models import User


class FormularioAsignar(forms.Form):
    """Empleado activo y fecha para una visita pendiente."""

    empleado = forms.ModelChoiceField(
        label="Empleado",
        queryset=User.objects.filter(rol=User.Rol.EMPLEADO, is_active=True).order_by(
            "username"
        ),
    )
    programada_para = forms.DateField(
        label="Fecha programada",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def clean_programada_para(self):
        fecha = self.cleaned_data["programada_para"]
        if fecha < timezone.localdate():
            raise forms.ValidationError("La fecha no puede ser anterior a hoy.")
        return fecha
