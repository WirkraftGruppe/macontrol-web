"""Rutas del panel de Visitas."""

from django.urls import path

from . import panel_views

app_name = "visitas"

urlpatterns = [
    path("", panel_views.ListadoVisitas.as_view(), name="listado"),
    path("<int:pk>/", panel_views.FichaVisita.as_view(), name="ficha"),
    path(
        "<int:pk>/revisar-incidencia/",
        panel_views.RevisarIncidencia.as_view(),
        name="revisar_incidencia",
    ),
    path("fotos/<uuid:codigo>/", panel_views.FotoVisita.as_view(), name="foto"),
    path(
        "proyectos/<int:proyecto_pk>/asignar/",
        panel_views.AsignarVisita.as_view(),
        name="asignar",
    ),
]
