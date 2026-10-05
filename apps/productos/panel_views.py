"""Vistas del panel de Productos: catálogo con alta y edición (sin borrado)."""

from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView

from apps.accounts.mixins import AdministradorRequeridoMixin
from apps.panel.listados import ListadoPanelMixin

from .models import Producto
from .panel_forms import ProductoForm


class ProductoListadoView(AdministradorRequeridoMixin, ListadoPanelMixin):
    model = Producto
    template_name = "productos/panel/listado.html"
    template_parcial = "productos/panel/_listado.html"
    orden_permitido = ("nombre_comercial", "principio_activo", "registro", "activo")
    campos_busqueda = ("nombre_comercial", "principio_activo", "registro")


class ProductoFormularioMixin(AdministradorRequeridoMixin):
    model = Producto
    form_class = ProductoForm
    template_name = "productos/panel/formulario.html"
    success_url = reverse_lazy("panel:productos:listado")

    def form_valid(self, form):
        messages.success(self.request, "Producto guardado.")
        return super().form_valid(form)


class ProductoAltaView(ProductoFormularioMixin, CreateView):
    titulo = "Nuevo producto"


class ProductoEditarView(ProductoFormularioMixin, UpdateView):
    titulo = "Editar producto"
