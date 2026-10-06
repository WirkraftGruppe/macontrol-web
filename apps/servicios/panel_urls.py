"""Rutas del panel de Servicios (planillas); ninguna ruta borra campos."""

from django.urls import path

from . import panel_views

app_name = "servicios"

urlpatterns = [
    path("", panel_views.TipoServicioListadoView.as_view(), name="listado"),
    path("<int:pk>/campos/", panel_views.CamposView.as_view(), name="campos"),
    path(
        "<int:pk>/campos/nuevo/",
        panel_views.CampoAltaView.as_view(),
        name="campo_alta",
    ),
    path(
        "campos/<int:pk>/editar/",
        panel_views.CampoEditarView.as_view(),
        name="campo_editar",
    ),
    path(
        "campos/<int:pk>/desactivar/",
        panel_views.CampoDesactivarView.as_view(),
        name="campo_desactivar",
    ),
    path(
        "campos/<int:pk>/reactivar/",
        panel_views.CampoReactivarView.as_view(),
        name="campo_reactivar",
    ),
]
