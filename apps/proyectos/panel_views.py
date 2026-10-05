"""Vistas del panel de Proyectos."""

from urllib.parse import urlencode

from django.db.models import F
from django.urls import reverse
from django.views.generic import CreateView, DetailView, UpdateView

from apps.accounts.mixins import AdministradorRequeridoMixin
from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.panel.listados import ListadoPanelMixin
from apps.servicios.models import TipoServicio
from apps.sitios.models import Sitio
from apps.visitas.planillas import filas_planilla

from .consultas import filtrar_por_estado_visita
from .models import FILTRO_ENCARGADO, EstadoVisita, Proyecto
from .panel_forms import FormularioProyectoAlta, FormularioProyectoEdicion

FILTROS = ("cliente", "sitio", "servicio", "estado", "encargado", "estado_visita")


class ListadoProyectos(AdministradorRequeridoMixin, ListadoPanelMixin):
    model = Proyecto
    template_name = "proyectos/panel/listado.html"
    template_parcial = "proyectos/panel/_listado.html"
    context_object_name = "proyectos"
    orden_permitido = ("titulo", "sitio__nombre", "proxima_visita", "estado")
    campos_busqueda = ("titulo", "sitio__nombre", "sitio__cliente__razon_social")

    def get_filtros(self):
        """Filtros activos del querystring (los vacíos se descartan)."""
        valores = {f: self.request.GET.get(f, "").strip() for f in FILTROS}
        return {f: v for f, v in valores.items() if v}

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related("sitio__cliente", "tipo_servicio", "encargado_actual")
        )
        filtros = self.get_filtros()
        for parametro, campo in (
            ("cliente", "sitio__cliente_id"),
            ("sitio", "sitio_id"),
            ("servicio", "tipo_servicio_id"),
            ("encargado", "encargado_actual_id"),
        ):
            valor = filtros.get(parametro)
            if valor and valor.isdigit():
                queryset = queryset.filter(**{campo: int(valor)})
        if filtros.get("estado") in Proyecto.Estado.values:
            queryset = queryset.filter(estado=filtros["estado"])
        queryset = filtrar_por_estado_visita(queryset, filtros.get("estado_visita"))
        if not self.get_orden():
            queryset = queryset.order_by(F("proxima_visita").asc(nulls_last=True), "pk")
        return queryset

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        filtros = self.get_filtros()
        for proyecto in contexto["proyectos"]:
            proyecto.etiqueta_visita = EstadoVisita(proyecto.estado_visita).label
        parametros = {"q": contexto["q"], "orden": contexto["orden"], **filtros}
        contexto["querystring"] = urlencode({k: v for k, v in parametros.items() if v})
        contexto["filtros"] = filtros
        contexto["clientes"] = Cliente.objects.order_by("razon_social")
        contexto["sitios"] = Sitio.objects.order_by("nombre")
        contexto["servicios"] = TipoServicio.objects.order_by("nombre")
        contexto["encargados"] = User.objects.filter(**FILTRO_ENCARGADO).order_by(
            "username"
        )
        contexto["estados"] = Proyecto.Estado.choices
        contexto["estados_visita"] = EstadoVisita.choices
        return contexto


class AltaProyecto(AdministradorRequeridoMixin, CreateView):
    model = Proyecto
    form_class = FormularioProyectoAlta
    template_name = "proyectos/panel/formulario.html"
    extra_context = {"titulo": "Nuevo proyecto"}

    def get_success_url(self):
        return reverse("panel:proyectos:ficha", args=[self.object.pk])


class EdicionProyecto(AdministradorRequeridoMixin, UpdateView):
    model = Proyecto
    form_class = FormularioProyectoEdicion
    template_name = "proyectos/panel/formulario.html"
    extra_context = {"titulo": "Editar proyecto"}

    def get_success_url(self):
        return reverse("panel:proyectos:ficha", args=[self.object.pk])


class FichaProyecto(AdministradorRequeridoMixin, DetailView):
    template_name = "proyectos/panel/ficha.html"
    context_object_name = "proyecto"
    queryset = Proyecto.objects.select_related(
        "sitio__cliente", "tipo_servicio", "encargado_actual"
    )

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        proyecto = contexto["proyecto"]
        visitas = list(
            proyecto.visitas.select_related("empleado")
            .prefetch_related(
                "revisiones__punto",
                "revisiones__fotos",
                "revisiones__productos__producto",
            )
            .order_by("-creado")
        )
        for visita in visitas:
            visita.filas = filas_planilla(visita.esquema_planilla, visita.datos)
            for revision in visita.revisiones.all():
                revision.filas = filas_planilla(
                    revision.esquema_planilla, revision.datos
                )
        contexto["visitas"] = visitas
        contexto["etiqueta_visita"] = EstadoVisita(proyecto.estado_visita).label
        return contexto
