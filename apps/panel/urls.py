"""Rutas del panel de gestión."""

from django.urls import path

from . import views

app_name = "panel"

urlpatterns = [
    path("", views.inicio, name="inicio"),
]
