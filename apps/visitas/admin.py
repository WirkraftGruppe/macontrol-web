from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Foto, ProductoAplicado, Visita

CAMPOS_EVIDENCIA = (
    "proyecto",
    "empleado",
    "origen",
    "motivo_manual",
    "latitud",
    "longitud",
    "precision_m",
    "datos",
    "estado",
    "realizada_en",
    "esquema_planilla",
)


def _visita_cerrada(visita):
    """Una visita ya no pendiente es evidencia: no se modifica."""
    return visita is not None and visita.estado != Visita.Estado.PENDIENTE


class InlineDeEvidencia:
    """Bloquea alta, cambio y borrado cuando la visita padre no está pendiente."""

    def has_add_permission(self, request, obj=None):
        return not _visita_cerrada(obj) and super().has_add_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        return not _visita_cerrada(obj) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return (
            False
            if _visita_cerrada(obj)
            else super().has_delete_permission(request, obj)
        )


class FotoInline(InlineDeEvidencia, admin.TabularInline):
    model = Foto
    extra = 0
    fields = ("imagen", "tomada_en", "orden")

    def has_delete_permission(self, request, obj=None):
        return False


class ProductoAplicadoInline(InlineDeEvidencia, admin.TabularInline):
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

    def get_readonly_fields(self, request, obj=None):
        if _visita_cerrada(obj):
            return CAMPOS_EVIDENCIA
        return super().get_readonly_fields(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Foto)
class FotoAdmin(admin.ModelAdmin):
    list_display = ("id", "visita", "tomada_en", "orden")
    raw_id_fields = ("visita",)
    readonly_fields = ("visita",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if obj is not None and _visita_cerrada(obj.visita):
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ProductoAplicado)
class ProductoAplicadoAdmin(admin.ModelAdmin):
    list_display = ("id", "visita", "producto", "lote", "dosis", "unidad")
    raw_id_fields = ("producto",)
    readonly_fields = ("visita",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if obj is not None and _visita_cerrada(obj.visita):
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)
