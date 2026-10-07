from django.contrib import admin

from .models import ClienteDestacado, Configuracion, PaginaServicio


@admin.register(Configuracion)
class ConfiguracionAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "telefono", "correo")

    def has_add_permission(self, request):
        return not Configuracion.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PaginaServicio)
class PaginaServicioAdmin(admin.ModelAdmin):
    list_display = ("titulo_seo", "tipo", "publicado")
    list_filter = ("publicado",)
    search_fields = ("titulo_seo", "tipo__nombre")


@admin.register(ClienteDestacado)
class ClienteDestacadoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "orden", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)
