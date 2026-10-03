"""Sitio de administración técnico: solo superusuarios activos."""

from django.contrib.admin import AdminSite


class SitioAdministracion(AdminSite):
    def has_permission(self, request):
        return request.user.is_active and request.user.is_superuser
