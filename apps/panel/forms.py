"""Formularios del panel."""

from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from apps.accounts.limites import normalizar_usuario


class FormularioIngreso(AuthenticationForm):
    """Login del panel: solo entran administradores."""

    def clean_username(self):
        return normalizar_usuario(self.cleaned_data["username"])

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.es_administrador:
            raise ValidationError(
                "Esta cuenta no tiene acceso al panel.", code="sin_acceso"
            )
