"""Vistas transversales del panel: inicio, ingreso y salida."""

from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponse
from django.views import View

from apps.accounts.limites import LimiteIngresoMixin
from apps.accounts.mixins import AdministradorRequeridoMixin

from .forms import FormularioIngreso


class InicioView(AdministradorRequeridoMixin, View):
    """Vista provisoria del panel: texto fijo, sin datos."""

    def get(self, request):
        return HttpResponse("Panel de gestión de MAControl S.A.")


class IngresarView(LimiteIngresoMixin, LoginView):
    template_name = "panel/ingresar.html"
    authentication_form = FormularioIngreso
    redirect_authenticated_user = False


class SalirView(LogoutView):
    """Cierra la sesión; solo acepta POST."""
