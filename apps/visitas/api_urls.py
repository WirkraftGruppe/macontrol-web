"""Rutas de API de Visitas (se montan en la raíz de la API)."""

from django.urls import path

from . import api_views

app_name = "visitas"

urlpatterns = [
    path("me/visitas/", api_views.MisVisitasView.as_view(), name="mis-visitas"),
    path("visitas/", api_views.CrearVisitaView.as_view(), name="crear"),
    path("me/historial/", api_views.HistorialView.as_view(), name="historial"),
    path("fotos/<uuid:codigo>/", api_views.FotoView.as_view(), name="foto"),
]
