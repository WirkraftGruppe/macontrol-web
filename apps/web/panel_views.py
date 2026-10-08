"""Vistas del panel para editar el contenido del sitio público."""

from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView

from apps.accounts.mixins import AdministradorRequeridoMixin
from apps.panel.listados import ListadoPanelMixin

from .forms import ClienteDestacadoForm, ConfiguracionForm, PaginaServicioForm
from .models import ClienteDestacado, Configuracion, PaginaServicio


class FormularioContenidoMixin(AdministradorRequeridoMixin):
    """Formulario con subida de archivos, aviso de guardado y plantilla común."""

    template_name = "web/panel/formulario.html"
    titulo = ""
    mensaje = "Cambios guardados."
    cancelar_url = None

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["titulo_pagina"] = self.titulo
        contexto["cancelar_url"] = self.cancelar_url
        return contexto

    def form_valid(self, form):
        messages.success(self.request, self.mensaje)
        return super().form_valid(form)


class ConfiguracionView(FormularioContenidoMixin, UpdateView):
    form_class = ConfiguracionForm
    titulo = "Configuración del sitio"
    success_url = reverse_lazy("panel:web:configuracion")

    def get_object(self, queryset=None):
        return Configuracion.obtener()


class PaginaListadoView(AdministradorRequeridoMixin, ListadoPanelMixin):
    queryset = PaginaServicio.objects.select_related("tipo")
    template_name = "web/panel/paginas.html"
    template_parcial = "web/panel/_paginas.html"
    orden_permitido = ("titulo_seo", "publicado")
    campos_busqueda = ("titulo_seo", "tipo__nombre")


class PaginaEditarView(FormularioContenidoMixin, UpdateView):
    model = PaginaServicio
    form_class = PaginaServicioForm
    titulo = "Editar página de servicio"
    success_url = reverse_lazy("panel:web:paginas")
    cancelar_url = reverse_lazy("panel:web:paginas")


class ClienteListadoView(AdministradorRequeridoMixin, ListadoPanelMixin):
    model = ClienteDestacado
    template_name = "web/panel/clientes.html"
    template_parcial = "web/panel/_clientes.html"
    orden_permitido = ("nombre", "orden", "activo")
    campos_busqueda = ("nombre",)


class ClienteAltaView(FormularioContenidoMixin, CreateView):
    model = ClienteDestacado
    form_class = ClienteDestacadoForm
    titulo = "Nuevo cliente destacado"
    success_url = reverse_lazy("panel:web:clientes")
    cancelar_url = reverse_lazy("panel:web:clientes")


class ClienteEditarView(FormularioContenidoMixin, UpdateView):
    model = ClienteDestacado
    form_class = ClienteDestacadoForm
    titulo = "Editar cliente destacado"
    success_url = reverse_lazy("panel:web:clientes")
    cancelar_url = reverse_lazy("panel:web:clientes")
