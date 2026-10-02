from django.contrib import admin

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "cuit", "contacto_nombre", "activo")
    search_fields = ("razon_social", "cuit", "contacto_nombre")
    list_filter = ("activo",)
