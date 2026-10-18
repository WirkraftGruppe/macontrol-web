"""Administración del contenido del sitio público, en español."""

from django.contrib import admin
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.urls import path
from django.utils.html import format_html

from . import views
from .forms import ClienteDestacadoForm, ConfiguracionForm, ServicioForm
from .models import ClienteDestacado, Configuracion, Servicio

admin.site.site_header = "Administración de MAControl"
admin.site.site_title = "MAControl"
admin.site.index_title = "Contenido del sitio"


def _borrar_al_confirmar(storage, nombres):
    """Borra archivos del storage recién cuando la transacción se confirma."""
    nombres = [nombre for nombre in nombres if nombre]
    if nombres:
        transaction.on_commit(lambda: [storage.delete(n) for n in nombres])


def _miniatura(imagen):
    """Imagen chica (hasta 160 x 80) para el admin, o un guion si no hay archivo."""
    if not imagen:
        return "—"
    try:
        escala = min(160 / imagen.width, 80 / imagen.height, 1)
        ancho, alto = round(imagen.width * escala), round(imagen.height * escala)
    except (OSError, ValueError):
        ancho, alto = 160, 80
    return format_html(
        '<img src="{}" alt="" width="{}" height="{}">', imagen.url, ancho, alto
    )


class BorraArchivosMixin:
    """Borra del storage los archivos reemplazados, quitados o de objetos borrados."""

    campos_archivo = ()

    def _nombres(self, obj):
        return {campo: getattr(obj, campo).name for campo in self.campos_archivo}

    def save_model(self, request, obj, form, change):
        anteriores = {}
        if change:
            anteriores = self._nombres(self.model.objects.get(pk=obj.pk))
        super().save_model(request, obj, form, change)
        for campo, anterior in anteriores.items():
            if anterior != getattr(obj, campo).name:
                _borrar_al_confirmar(getattr(obj, campo).storage, [anterior])

    def delete_model(self, request, obj):
        nombres = self._nombres(obj)
        super().delete_model(request, obj)
        for campo, nombre in nombres.items():
            _borrar_al_confirmar(getattr(obj, campo).storage, [nombre])

    def delete_queryset(self, request, queryset):
        objetos = list(queryset)
        super().delete_queryset(request, queryset)
        for obj in objetos:
            for campo, nombre in self._nombres(obj).items():
                _borrar_al_confirmar(getattr(obj, campo).storage, [nombre])


@admin.register(Configuracion)
class ConfiguracionAdmin(admin.ModelAdmin):
    form = ConfiguracionForm
    list_display = ("razon_social", "telefono", "correo")
    fieldsets = (
        (
            "Contacto",
            {
                "fields": (
                    "razon_social",
                    "eslogan",
                    "presentacion",
                    "telefono",
                    "whatsapp",
                    "correo",
                    "horario",
                )
            },
        ),
        ("Datos legales", {"fields": ("habilitacion", "ley", "director_tecnico")}),
        ("Redes y direcciones", {"fields": ("direcciones", "redes")}),
    )

    def has_add_permission(self, request):
        return not Configuracion.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Servicio)
class ServicioAdmin(BorraArchivosMixin, admin.ModelAdmin):
    form = ServicioForm
    campos_archivo = ("foto",)
    list_display = ("nombre", "orden", "publicado")
    list_editable = ("orden", "publicado")
    list_filter = ("publicado",)
    search_fields = ("nombre", "titulo_seo")
    prepopulated_fields = {"slug": ("nombre",)}
    readonly_fields = ("miniatura",)
    fieldsets = (
        (None, {"fields": ("nombre", "slug", "titulo_seo", "resumen", "problema")}),
        ("Contenido", {"fields": ("adicional", "metodos", "faq", "sectores")}),
        ("Portada", {"fields": ("foto", "miniatura")}),
        ("Publicación", {"fields": ("orden", "publicado")}),
    )

    @admin.display(description="vista previa de la foto")
    def miniatura(self, obj):
        return _miniatura(obj.foto) if obj else "—"

    def get_urls(self):
        vista_previa = path(
            "<int:pk>/vista-previa/",
            self.admin_site.admin_view(self.vista_previa),
            name="web_servicio_vista_previa",
        )
        return [vista_previa, *super().get_urls()]

    def vista_previa(self, request, pk):
        """Página pública del servicio, publicado o no, fuera de los buscadores."""
        servicio = get_object_or_404(Servicio, pk=pk)
        respuesta = views._pagina(
            request, "web/paginas/servicio.html", **views.contexto_servicio(servicio)
        )
        respuesta["X-Robots-Tag"] = "noindex"
        return respuesta


@admin.register(ClienteDestacado)
class ClienteDestacadoAdmin(BorraArchivosMixin, admin.ModelAdmin):
    form = ClienteDestacadoForm
    campos_archivo = ("logo",)
    list_display = ("nombre", "orden", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)
    readonly_fields = ("miniatura",)
    fields = ("nombre", "logo", "miniatura", "orden", "activo")

    @admin.display(description="vista previa del logo")
    def miniatura(self, obj):
        return _miniatura(obj.logo) if obj else "—"
