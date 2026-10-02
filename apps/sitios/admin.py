from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from . import services
from .models import Sitio


@admin.register(Sitio)
class SitioAdmin(SimpleHistoryAdmin):
    list_display = ("nombre", "cliente", "localidad", "sector", "activo")
    search_fields = ("nombre", "direccion", "localidad", "cliente__razon_social")
    list_filter = ("sector", "activo")
    readonly_fields = ("qr_codigo",)
    actions = ["regenerar_qr"]

    @admin.action(description="Regenerar código QR (invalida la etiqueta impresa)")
    def regenerar_qr(self, request, queryset):
        cantidad = 0
        for sitio in queryset:
            services.regenerar_qr(sitio)
            cantidad += 1
        self.message_user(request, f"Se regeneró el código QR de {cantidad} sitio(s).")
