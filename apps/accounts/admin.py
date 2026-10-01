from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CuentaAdmin(UserAdmin):
    """Admin de usuarios con los campos de rol y teléfono."""

    list_display = ("username", "first_name", "last_name", "rol", "is_active")
    list_filter = ("rol", "is_active", "is_staff")
    fieldsets = UserAdmin.fieldsets + (("MAControl", {"fields": ("rol", "telefono")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("MAControl", {"fields": ("rol", "telefono")}),
    )
