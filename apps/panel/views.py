"""Vistas transversales del panel: tablero, mapa, ingreso y salida."""

from csp.decorators import csp_update
from django.contrib.auth.views import LoginView, LogoutView
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.limites import LimiteIngresoMixin
from apps.accounts.mixins import AdministradorRequeridoMixin
from apps.proyectos.models import EstadoVisita
from apps.servicios.models import TipoServicio

from .forms import FormularioIngreso
from .mapa import ORIGEN_TESELAS, sitios_para_mapa
from .tablero import contadores, proyectos_urgentes


class InicioView(AdministradorRequeridoMixin, TemplateView):
    """Tablero: contadores y los proyectos activos más urgentes."""

    template_name = "panel/tablero.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["contadores"] = contadores()
        contexto["urgentes"] = proyectos_urgentes()
        return contexto


@method_decorator(csp_update({"img-src": ORIGEN_TESELAS}), name="dispatch")
class MapaView(AdministradorRequeridoMixin, TemplateView):
    """Página del mapa; los sitios se piden a `MapaDatosView`."""

    template_name = "panel/mapa.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["servicios"] = TipoServicio.objects.order_by("nombre")
        contexto["estados"] = EstadoVisita.choices
        return contexto


@method_decorator(csp_update({"img-src": ORIGEN_TESELAS}), name="dispatch")
class MapaDatosView(AdministradorRequeridoMixin, View):
    """JSON con los sitios activos; filtros `cliente`, `servicio` y `estado`."""

    def get(self, request):
        estado = request.GET.get("estado")
        if estado not in EstadoVisita.values:
            estado = None
        sitios = sitios_para_mapa(
            cliente=_entero(request.GET.get("cliente")),
            servicio=_entero(request.GET.get("servicio")),
            estado=estado,
        )
        return JsonResponse({"sitios": sitios})


def _entero(valor):
    """Devuelve el entero o None si el parámetro falta o no es numérico."""
    return int(valor) if valor and valor.isdigit() else None


class IngresarView(LimiteIngresoMixin, LoginView):
    template_name = "panel/ingresar.html"
    authentication_form = FormularioIngreso
    redirect_authenticated_user = False


class SalirView(LogoutView):
    """Cierra la sesión; solo acepta POST."""
