from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Foto, ProductoAplicado, Visita


class FotoInline(admin.TabularInline):
    model = Foto
    extra = 0
    fields = ("imagen", "tomada_en", "orden")


class ProductoAplicadoInline(admin.TabularInline):
    model = ProductoAplicado
    extra = 0
    fields = ("producto", "lote", "dosis", "unidad", "cantidad")
    raw_id_fields = ("producto",)


@admin.register(Visita)
class VisitaAdmin(SimpleHistoryAdmin):
    list_display = (
        "id",
        "proyecto",
        "empleado",
        "origen",
        "estado",
        "programada_para",
        "realizada_en",
        "incidencia",
    )
    list_filter = ("estado", "origen", "incidencia")
    search_fields = ("proyecto__titulo", "empleado__username")
    raw_id_fields = ("proyecto",)
    readonly_fields = ("estado", "realizada_en", "esquema_planilla")
    inlines = (FotoInline, ProductoAplicadoInline)


@admin.register(Foto)
class FotoAdmin(admin.ModelAdmin):
    list_display = ("id", "visita", "tomada_en", "orden")
    raw_id_fields = ("visita",)


@admin.register(ProductoAplicado)
class ProductoAplicadoAdmin(admin.ModelAdmin):
    list_display = ("id", "visita", "producto", "lote", "dosis", "unidad")
    raw_id_fields = ("visita", "producto")
