from django.contrib.auth.mixins import UserPassesTestMixin


class AdministradorRequeridoMixin(UserPassesTestMixin):
    """Solo usuarios activos con rol administrador; anónimo al login, otros 403."""

    def test_func(self):
        usuario = self.request.user
        return bool(
            usuario.is_authenticated and usuario.is_active and usuario.es_administrador
        )
