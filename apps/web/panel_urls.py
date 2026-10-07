"""Rutas del panel de Web: configuración, páginas de servicio y clientes."""

from django.urls import path

from . import panel_views as vistas

app_name = "web"

urlpatterns = [
    path("configuracion/", vistas.ConfiguracionView.as_view(), name="configuracion"),
    path("paginas/", vistas.PaginaListadoView.as_view(), name="paginas"),
    path("paginas/<int:pk>/", vistas.PaginaEditarView.as_view(), name="pagina_editar"),
    path("clientes/", vistas.ClienteListadoView.as_view(), name="clientes"),
    path("clientes/nuevo/", vistas.ClienteAltaView.as_view(), name="cliente_alta"),
    path(
        "clientes/<int:pk>/", vistas.ClienteEditarView.as_view(), name="cliente_editar"
    ),
]
