from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.template.response import TemplateResponse
from simple_history.admin import SimpleHistoryAdmin

from . import services
from .models import Sitio


@admin.register(Sitio)
class SitioAdmin(SimpleHistoryAdmin):
    list_display = ("nombre", "cliente", "localidad", "sector", "activo")
    search_fields = ("nombre", "direccion", "localidad", "cliente__razon_social")
    list_filter = ("sector", "activo")
    readonly_fields = ("qr_codigo",)
    actions = ["regenerar_qr", "suprimir_datos"]

    def _es_administrador_activo(self, request):
        return request.user.is_active and getattr(
            request.user, "es_administrador", False
        )

    def has_regenerar_qr_permission(self, request):
        return self._es_administrador_activo(request) and self.has_change_permission(
            request
        )

    def has_suprimir_datos_permission(self, request):
        return self._es_administrador_activo(request) and self.has_delete_permission(
            request
        )

    def _pedir_confirmacion(self, request, queryset, accion, titulo, consecuencia):
        return TemplateResponse(
            request,
            "admin/sitios/sitio/confirmar_accion.html",
            {
                "title": titulo,
                "consecuencia": consecuencia,
                "sitios": queryset,
                "accion": accion,
                "opts": self.model._meta,
                "action_checkbox_name": admin.helpers.ACTION_CHECKBOX_NAME,
                **self.admin_site.each_context(request),
            },
        )

    @admin.action(
        description="Regenerar código QR (invalida la etiqueta impresa)",
        permissions=["regenerar_qr"],
    )
    def regenerar_qr(self, request, queryset):
        if "confirmado" not in request.POST:
            return self._pedir_confirmacion(
                request,
                queryset,
                "regenerar_qr",
                "Regenerar código QR",
                "La etiqueta QR impresa de estos sitios dejará de funcionar "
                "y habrá que imprimir una nueva.",
            )
        try:
            cantidad = services.regenerar_qr_lote(list(queryset))
        except ValidationError as error:
            self.message_user(request, " ".join(error.messages), level=messages.ERROR)
            return
        self.message_user(request, f"Se regeneró el código QR de {cantidad} sitio(s).")

    @admin.action(
        description="Suprimir datos (Ley 25.326): borra el sitio y todo su historial",
        permissions=["suprimir_datos"],
    )
    def suprimir_datos(self, request, queryset):
        if "confirmado" not in request.POST:
            return self._pedir_confirmacion(
                request,
                queryset,
                "suprimir_datos",
                "Suprimir datos (Ley 25.326)",
                "Se borrarán estos sitios y todo su historial de cambios. "
                "No se puede deshacer.",
            )
        suprimidos, con_proyectos = services.suprimir_sitios(list(queryset))
        self.message_user(
            request, f"Se suprimieron los datos de {suprimidos} sitio(s)."
        )
        if con_proyectos:
            nombres = ", ".join(sitio.nombre for sitio in con_proyectos)
            self.message_user(
                request,
                f"No se suprimieron por tener proyectos asociados: {nombres}.",
                level=messages.WARNING,
            )
