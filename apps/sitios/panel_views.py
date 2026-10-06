"""Vistas del panel de Sitios (solo administradores)."""

from csp.decorators import csp_update
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.views import View
from django.views.generic import CreateView, DetailView, UpdateView
from django.views.generic.detail import SingleObjectMixin

from apps.accounts.mixins import AdministradorRequeridoMixin
from apps.clientes.models import Cliente
from apps.panel.listados import ListadoPanelMixin
from apps.panel.mapa import ORIGEN_TESELAS

from . import geocodificacion, qr, services
from .estado import EstadoPunto, estados_de_puntos
from .models import Plano, PuntoControl, Sitio
from .panel_forms import (
    PlanoForm,
    PosicionForm,
    PuntoAltaForm,
    PuntoForm,
    SitioForm,
    UbicacionForm,
)

PESTANAS = ("mapa", "planos", "puntos")
CLASE_ESTADO = {
    EstadoPunto.AL_DIA: "ok",
    EstadoPunto.PROXIMA: "warn",
    EstadoPunto.VENCIDA: "danger",
    EstadoPunto.SIN_REVISAR: "neutral",
}


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


def _numero(valor):
    """Decimal de la base a número de JSON; vacío queda en ``None``."""
    return None if valor is None else float(valor)


@method_decorator(csp_update({"img-src": ORIGEN_TESELAS}), name="dispatch")
class SitioFicha(AdministradorRequeridoMixin, DetailView):
    """Ficha con pestañas ``?pestana=mapa|planos|puntos`` (por defecto, puntos)."""

    model = Sitio
    template_name = "sitios/panel/ficha.html"

    def get_queryset(self):
        return Sitio.objects.select_related("cliente")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        sitio = self.object
        pestana = self.request.GET.get("pestana", "puntos")
        if pestana not in PESTANAS:
            pestana = "puntos"
        puntos = list(sitio.puntos.select_related("plano"))
        activos = [p for p in puntos if p.activo]
        estados = estados_de_puntos(activos)
        for punto in puntos:
            estado = estados.get(punto.pk)
            punto.estado = estado
            punto.estado_etiqueta = EstadoPunto(estado).label if estado else ""
            punto.estado_clase = CLASE_ESTADO.get(estado, "neutral")
        planos = list(sitio.planos.filter(activo=True))
        pk_plano = self.request.GET.get("plano", "")
        plano = next((p for p in planos if str(p.pk) == pk_plano), None)
        plano = plano or (planos[0] if planos else None)
        contexto.update(
            proyectos=sitio.proyectos.select_related("tipo_servicio"),
            pestana=pestana,
            pestanas=(("puntos", "Puntos"), ("mapa", "Mapa"), ("planos", "Planos")),
            puntos=puntos,
            puntos_activos=activos,
            con_propuesta=[p for p in activos if p.ubicacion_propuesta],
            planos=planos,
            plano=plano,
        )
        if pestana == "mapa":
            contexto["datos_mapa"] = self._datos_mapa(sitio, activos)
        if pestana == "planos" and plano:
            contexto["datos_plano"] = self._datos_plano(plano, activos)
        return contexto

    @staticmethod
    def _datos_mapa(sitio, puntos):
        return {
            "centro": [_numero(sitio.latitud), _numero(sitio.longitud)],
            "puntos": [
                {
                    "id": p.pk,
                    "nombre": p.nombre,
                    "lat": _numero(p.latitud),
                    "lng": _numero(p.longitud),
                    "estado": p.estado,
                    "url": reverse("panel:sitios:punto_ubicacion", args=[p.pk]),
                }
                for p in puntos
            ],
        }

    @staticmethod
    def _datos_plano(plano, puntos):
        return {
            "imagen": reverse("panel:sitios:plano_imagen", args=[plano.pk]),
            "ancho": plano.ancho_px,
            "alto": plano.alto_px,
            "plano": plano.pk,
            "puntos": [
                {
                    "id": p.pk,
                    "nombre": p.nombre,
                    "x": _numero(p.x),
                    "y": _numero(p.y),
                    "estado": p.estado,
                    "url": reverse("panel:sitios:punto_posicion", args=[p.pk]),
                }
                for p in puntos
                if p.plano_id == plano.pk
            ],
        }


def _url_ficha(sitio_pk, pestana, plano_pk=None):
    url = f"{reverse('panel:sitios:ficha', args=[sitio_pk])}?pestana={pestana}"
    return f"{url}&plano={plano_pk}" if plano_pk else url


class _PuntoMixin(AdministradorRequeridoMixin):
    """Obtiene el punto de la URL, con su sitio."""

    model = PuntoControl

    def get_queryset(self):
        return PuntoControl.objects.select_related("sitio", "plano")


class PuntoAlta(AdministradorRequeridoMixin, CreateView):
    """Alta de un punto; con ``plano``, ``x`` e ``y`` es el clic sobre el plano."""

    form_class = PuntoAltaForm
    template_name = "sitios/panel/punto_formulario.html"

    @cached_property
    def sitio(self):
        """Se busca recién tras la autorización: el anónimo no distingue ids."""
        return get_object_or_404(Sitio, pk=self.kwargs["pk"])

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "sitio": self.sitio}

    def get_initial(self):
        return {"activo": True, "orden": self.sitio.puntos.count()}

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update(titulo="Nuevo punto", sitio=self.sitio, es_alta=True)
        return contexto

    def get_success_url(self):
        punto = self.object
        if punto.plano_id:
            return _url_ficha(self.sitio.pk, "planos", punto.plano_id)
        return _url_ficha(self.sitio.pk, "puntos")


class PuntoEdicion(_PuntoMixin, UpdateView):
    form_class = PuntoForm
    template_name = "sitios/panel/punto_formulario.html"

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "sitio": self.object.sitio}

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update(titulo=f"Editar {self.object.nombre}", sitio=self.object.sitio)
        return contexto

    def get_success_url(self):
        return _url_ficha(self.object.sitio_id, "puntos")


class PuntoDesactivar(_PuntoMixin, DetailView):
    """GET pide confirmación; POST desactiva el punto."""

    template_name = "sitios/panel/punto_desactivar.html"

    def post(self, request, pk):
        punto = self.get_object()
        services.desactivar_punto(punto)
        messages.success(request, f"Se desactivó el punto {punto.nombre}.")
        return redirect(_url_ficha(punto.sitio_id, "puntos"))


class PuntoQRPng(_PuntoMixin, DetailView):
    """PNG del QR del punto: descarga, o inline con ``?inline=1``."""

    def render_to_response(self, context, **kwargs):
        punto = self.object
        respuesta = HttpResponse(qr.png_qr(punto), content_type="image/png")
        nombre = slugify(f"{punto.sitio.nombre} {punto.nombre}") or "punto"
        modo = "inline" if self.request.GET.get("inline") else "attachment"
        respuesta["Content-Disposition"] = f'{modo}; filename="qr-{nombre}.png"'
        respuesta["Cache-Control"] = "private, no-store"
        return respuesta


class PuntoRegenerarQR(_PuntoMixin, DetailView):
    """GET pide confirmación; POST regenera el código e invalida la etiqueta."""

    template_name = "sitios/panel/regenerar_qr.html"

    def post(self, request, pk):
        punto = self.get_object()
        services.regenerar_qr(punto)
        messages.success(
            request, "Se generó un nuevo QR; la etiqueta anterior ya no sirve."
        )
        return redirect(_url_ficha(punto.sitio_id, "puntos"))


class _AccionPunto(_PuntoMixin, SingleObjectMixin, View):
    """Acción POST sobre un punto, para HTMX o para un botón de la ficha."""

    http_method_names = ["post"]


class PuntoPosicion(_AccionPunto):
    """Guarda la posición (x, y en fracción 0 a 1) del marcador en el plano."""

    def post(self, request, pk):
        punto = self.get_object()
        form = PosicionForm(request.POST)
        if not punto.plano_id or not form.is_valid():
            return JsonResponse({"error": "Posición inválida."}, status=400)
        services.mover_en_plano(punto, form.cleaned_data["x"], form.cleaned_data["y"])
        return JsonResponse({"x": _numero(punto.x), "y": _numero(punto.y)})


class PuntoUbicacion(_AccionPunto):
    """Fija lat/lng del punto con el clic en el mapa."""

    def post(self, request, pk):
        punto = self.get_object()
        form = UbicacionForm(request.POST)
        if not form.is_valid():
            return JsonResponse({"error": "Coordenadas inválidas."}, status=400)
        services.fijar_ubicacion(
            punto, form.cleaned_data["latitud"], form.cleaned_data["longitud"]
        )
        return JsonResponse(
            {"lat": _numero(punto.latitud), "lng": _numero(punto.longitud)}
        )


class PuntoPropuesta(_AccionPunto):
    """Acepta o descarta la ubicación propuesta por una revisión."""

    def post(self, request, pk):
        punto = self.get_object()
        accion = request.POST.get("accion")
        if accion not in ("aceptar", "descartar"):
            return JsonResponse({"error": "Acción inválida."}, status=400)
        if accion == "aceptar":
            try:
                services.aceptar_ubicacion_propuesta(punto)
            except ValidationError as error:
                messages.error(request, error.messages[0])
            else:
                messages.success(request, "Ubicación aceptada.")
        else:
            services.descartar_ubicacion_propuesta(punto)
            messages.success(request, "Ubicación descartada.")
        return redirect(_url_ficha(punto.sitio_id, "mapa"))


class PlanoAlta(AdministradorRequeridoMixin, CreateView):
    """Sube un plano (JPG, PNG o PDF); ``Plano`` lo valida y lo guarda como PNG."""

    form_class = PlanoForm
    template_name = "sitios/panel/plano_formulario.html"

    @cached_property
    def sitio(self):
        """Se busca recién tras la autorización: el anónimo no distingue ids."""
        return get_object_or_404(Sitio, pk=self.kwargs["pk"])

    def form_valid(self, form):
        form.instance.sitio = self.sitio
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update(titulo="Subir plano", sitio=self.sitio)
        return contexto

    def get_success_url(self):
        return _url_ficha(self.sitio.pk, "planos", self.object.pk)


class PlanoImagen(AdministradorRequeridoMixin, View):
    """Imagen del plano para el editor: autenticada, nunca desde MEDIA público."""

    def get(self, request, pk):
        plano = get_object_or_404(Plano, pk=pk)
        try:
            archivo = plano.imagen.open("rb")
        except FileNotFoundError:
            raise Http404 from None
        respuesta = FileResponse(archivo, content_type="image/png")
        respuesta["Cache-Control"] = "private, no-store"
        respuesta["X-Content-Type-Options"] = "nosniff"
        return respuesta


class Geocodificar(AdministradorRequeridoMixin, View):
    """Candidatos de Nominatim; solo POST (con CSRF) y el texto va en el cuerpo."""

    http_method_names = ["post", "options"]

    def post(self, request):
        try:
            candidatos = geocodificacion.buscar(request.POST.get("q", ""))
        except geocodificacion.TextoInvalido:
            return JsonResponse(
                {"error": "Escriba una dirección de hasta 200 caracteres."}, status=400
            )
        except geocodificacion.GeocodificacionError:
            return JsonResponse(
                {"error": geocodificacion.MENSAJE_CARGA_MANUAL}, status=503
            )
        return JsonResponse({"resultados": candidatos})
