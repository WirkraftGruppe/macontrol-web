"""Rutas del panel de Proyectos."""

from django.urls import path

from . import panel_views as views

app_name = "proyectos"

urlpatterns = [
    path("", views.ListadoProyectos.as_view(), name="listado"),
    path("nuevo/", views.AltaProyecto.as_view(), name="alta"),
    path("<int:pk>/", views.FichaProyecto.as_view(), name="ficha"),
    path("<int:pk>/editar/", views.EdicionProyecto.as_view(), name="editar"),
]
