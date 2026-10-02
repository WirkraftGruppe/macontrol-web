from django.contrib import admin

from .models import Producto


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre_comercial", "principio_activo", "registro", "activo")
    search_fields = ("nombre_comercial", "principio_activo", "registro")
    list_filter = ("activo",)
