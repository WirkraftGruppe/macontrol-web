"""Rutas del panel de Usuarios."""

from django.urls import path

from . import panel_views as vistas

app_name = "usuarios"

urlpatterns = [
    path("", vistas.UsuarioListadoView.as_view(), name="listado"),
    path("nuevo/", vistas.UsuarioAltaView.as_view(), name="alta"),
    path("<int:pk>/editar/", vistas.UsuarioEditarView.as_view(), name="editar"),
    path(
        "<int:pk>/desactivar/",
        vistas.UsuarioDesactivarView.as_view(),
        name="desactivar",
    ),
    path(
        "<int:pk>/reactivar/",
        vistas.UsuarioReactivarView.as_view(),
        name="reactivar",
    ),
    path(
        "<int:pk>/contrasena/",
        vistas.UsuarioContrasenaView.as_view(),
        name="contrasena",
    ),
]
