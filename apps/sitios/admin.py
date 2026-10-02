from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Sitio


@admin.register(Sitio)
class SitioAdmin(SimpleHistoryAdmin):
    list_display = ("nombre", "cliente", "localidad", "sector", "activo")
    search_fields = ("nombre", "direccion", "localidad", "cliente__razon_social")
    list_filter = ("sector", "activo")
    readonly_fields = ("qr_codigo",)
