"""Rutas de API de Productos."""

from django.urls import path

from . import api_views

app_name = "productos"

urlpatterns = [
    path("", api_views.CatalogoView.as_view(), name="catalogo"),
]
