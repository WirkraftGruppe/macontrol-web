from rest_framework.permissions import BasePermission


class EsAdministrador(BasePermission):
    """Permite el acceso solo a usuarios autenticados con rol administrador."""

    def has_permission(self, request, view):
        usuario = request.user
        return bool(usuario and usuario.is_authenticated and usuario.es_administrador)


class EsEmpleado(BasePermission):
    """Permite el acceso solo a usuarios autenticados con rol empleado."""

    def has_permission(self, request, view):
        usuario = request.user
        return bool(usuario and usuario.is_authenticated and usuario.es_empleado)
