"""Administración del contenido del sitio público, en español."""

from django.contrib import admin
from django.shortcuts import get_object_or_404
from django.urls import path
from django.utils.html import format_html

from . import views
from .forms import ClienteDestacadoForm, ConfiguracionForm, ServicioForm
from .models import ClienteDestacado, Configuracion, Sector, Servicio

admin.site.site_header = "Administración de MAControl"
admin.site.site_title = "MAControl"
admin.site.index_title = "Contenido del sitio"


def _miniatura(imagen):
    """Imagen chica para el admin, o un guion si no hay archivo."""
    if not imagen:
        return "—"
    return format_html(
        '<img src="{}" alt="" style="max-height: 80px; max-width: 160px;">',
        imagen.url,
    )


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
class ServicioAdmin(admin.ModelAdmin):
    form = ServicioForm
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
        if servicio.foto:
            portada = {"url": servicio.foto.url, "ancho": 1200, "alto": 675}
        else:
            clave = views.PORTADA_POR_SLUG.get(servicio.slug, "hero")
            portada = views._imagen(clave)
        respuesta = views._pagina(
            request,
            "web/paginas/servicio.html",
            titulo=servicio.titulo_seo or servicio.nombre,
            descripcion=servicio.resumen,
            ruta=servicio.get_absolute_url(),
            og_imagen=portada["url"],
            pagina=servicio,
            portada=portada,
            sectores=[
                Sector(valor).label
                for valor in servicio.sectores
                if valor in Sector.values
            ],
            relacionados=Servicio.objects.publicados().exclude(pk=servicio.pk),
        )
        respuesta["X-Robots-Tag"] = "noindex"
        return respuesta


@admin.register(ClienteDestacado)
class ClienteDestacadoAdmin(admin.ModelAdmin):
    form = ClienteDestacadoForm
    list_display = ("nombre", "orden", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)
    readonly_fields = ("miniatura",)
    fields = ("nombre", "logo", "miniatura", "orden", "activo")

    @admin.display(description="vista previa del logo")
    def miniatura(self, obj):
        return _miniatura(obj.logo) if obj else "—"
