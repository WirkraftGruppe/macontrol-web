"""Rutas del panel de Clientes."""

from django.urls import path

from . import panel_views as vistas

app_name = "clientes"

urlpatterns = [
    path("", vistas.ClienteListadoView.as_view(), name="listado"),
    path("nuevo/", vistas.ClienteAltaView.as_view(), name="alta"),
    path("<int:pk>/", vistas.ClienteFichaView.as_view(), name="ficha"),
    path("<int:pk>/editar/", vistas.ClienteEditarView.as_view(), name="editar"),
    path("<int:pk>/baja/", vistas.ClienteBajaView.as_view(), name="baja"),
]
