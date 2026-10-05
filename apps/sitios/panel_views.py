"""Vistas del panel de Sitios (solo administradores)."""

from csp.decorators import csp_update
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.views import View
from django.views.generic import CreateView, DetailView, UpdateView

from apps.accounts.mixins import AdministradorRequeridoMixin
from apps.clientes.models import Cliente
from apps.panel.listados import ListadoPanelMixin
from apps.panel.mapa import ORIGEN_TESELAS

from . import geocodificacion, qr, services
from .models import Sitio
from .panel_forms import SitioForm


class SitioListado(AdministradorRequeridoMixin, ListadoPanelMixin):
    model = Sitio
    template_name = "sitios/panel/listado.html"
    template_parcial = "sitios/panel/_listado.html"
    orden_permitido = ("nombre", "cliente__razon_social", "localidad", "sector")
    campos_busqueda = ("nombre", "direccion", "localidad", "cliente__razon_social")

    def get_queryset(self):
        queryset = super().get_queryset().select_related("cliente")
        cliente = self.request.GET.get("cliente", "")
        if cliente.isdigit():
            queryset = queryset.filter(cliente_id=cliente)
        activo = self.request.GET.get("activo", "")
        if activo in ("1", "0"):
            queryset = queryset.filter(activo=activo == "1")
        return queryset

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["clientes"] = Cliente.objects.order_by("razon_social")
        contexto["cliente"] = self.request.GET.get("cliente", "")
        contexto["activo"] = self.request.GET.get("activo", "")
        return contexto


@method_decorator(csp_update({"img-src": ORIGEN_TESELAS}), name="dispatch")
class SitioAlta(AdministradorRequeridoMixin, CreateView):
    model = Sitio
    form_class = SitioForm
    template_name = "sitios/panel/formulario.html"
    extra_context = {"titulo": "Nuevo sitio"}

    def get_success_url(self):
        return reverse("panel:sitios:ficha", args=[self.object.pk])


@method_decorator(csp_update({"img-src": ORIGEN_TESELAS}), name="dispatch")
class SitioEdicion(AdministradorRequeridoMixin, UpdateView):
    model = Sitio
    form_class = SitioForm
    template_name = "sitios/panel/formulario.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["titulo"] = f"Editar {self.object.nombre}"
        return contexto

    def get_success_url(self):
        return reverse("panel:sitios:ficha", args=[self.object.pk])


class SitioFicha(AdministradorRequeridoMixin, DetailView):
    model = Sitio
    template_name = "sitios/panel/ficha.html"

    def get_queryset(self):
        return Sitio.objects.select_related("cliente")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["proyectos"] = self.object.proyectos.select_related("tipo_servicio")
        return contexto


class QRPng(AdministradorRequeridoMixin, View):
    """PNG del QR: descarga por defecto, o inline con ``?inline=1`` para la ficha."""

    def get(self, request, pk):
        sitio = get_object_or_404(Sitio, pk=pk)
        respuesta = HttpResponse(qr.png_qr(sitio), content_type="image/png")
        nombre = slugify(sitio.nombre) or "sitio"
        modo = "inline" if request.GET.get("inline") else "attachment"
        respuesta["Content-Disposition"] = f'{modo}; filename="qr-{nombre}.png"'
        respuesta["Cache-Control"] = "private, no-store"
        return respuesta


qr_png = QRPng.as_view()


class RegenerarQR(AdministradorRequeridoMixin, DetailView):
    """GET pide confirmación; POST regenera el código e invalida la etiqueta."""

    model = Sitio
    template_name = "sitios/panel/regenerar_qr.html"

    def post(self, request, pk):
        sitio = get_object_or_404(Sitio, pk=pk)
        services.regenerar_qr(sitio)
        messages.success(
            request, "Se generó un nuevo QR; la etiqueta anterior ya no sirve."
        )
        return redirect("panel:sitios:ficha", pk=sitio.pk)


class Geocodificar(AdministradorRequeridoMixin, View):
    """Candidatos de Nominatim para ``?q=``; solo se envía el texto de dirección."""

    def get(self, request):
        try:
            candidatos = geocodificacion.buscar(request.GET.get("q", ""))
        except geocodificacion.TextoInvalido:
            return JsonResponse(
                {"error": "Escriba una dirección de hasta 200 caracteres."}, status=400
            )
        except geocodificacion.GeocodificacionError:
            return JsonResponse(
                {"error": geocodificacion.MENSAJE_CARGA_MANUAL}, status=503
            )
        return JsonResponse({"resultados": candidatos})
