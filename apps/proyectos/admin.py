from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Proyecto


@admin.register(Proyecto)
class ProyectoAdmin(SimpleHistoryAdmin):
    list_display = (
        "titulo",
        "sitio",
        "tipo_servicio",
        "estado",
        "proxima_visita",
        "encargado_actual",
    )
    search_fields = ("titulo", "sitio__nombre", "sitio__cliente__razon_social")
    list_filter = ("estado", "tipo_servicio")
    raw_id_fields = ("sitio",)
