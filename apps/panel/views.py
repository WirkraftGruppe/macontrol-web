"""Vistas transversales del panel: inicio, ingreso y salida."""

from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponse
from django.views import View
from rest_framework.throttling import SimpleRateThrottle

from apps.accounts.mixins import AdministradorRequeridoMixin

from .forms import FormularioIngreso


class InicioView(AdministradorRequeridoMixin, View):
    """Vista provisoria del panel: texto fijo, sin datos."""

    def get(self, request):
        return HttpResponse("Panel de gestión de MAControl S.A.")


class LimiteIngresoPorIP(SimpleRateThrottle):
    """Limita los intentos de ingreso al panel por dirección IP."""

    scope = "autenticacion"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class LimiteIngresoPorUsuario(SimpleRateThrottle):
    """Limita los intentos de ingreso al panel por nombre de usuario."""

    scope = "autenticacion"

    def get_cache_key(self, request, view):
        usuario = request.POST.get("username", "").strip().lower()
        return self.cache_format % {"scope": self.scope, "ident": f"usuario:{usuario}"}


class IngresarView(LoginView):
    template_name = "panel/ingresar.html"
    authentication_form = FormularioIngreso
    redirect_authenticated_user = False

    def post(self, request, *args, **kwargs):
        for clase in (LimiteIngresoPorIP, LimiteIngresoPorUsuario):
            if not clase().allow_request(request, self):
                return HttpResponse(
                    "Demasiados intentos. Espere un minuto e intente de nuevo.",
                    status=429,
                    content_type="text/plain; charset=utf-8",
                )
        return super().post(request, *args, **kwargs)


class SalirView(LogoutView):
    """Cierra la sesión; solo acepta POST."""
