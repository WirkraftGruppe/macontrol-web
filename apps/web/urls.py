"""Rutas del sitio público."""

from django.urls import path

from . import views

app_name = "web"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("q/<uuid:codigo>/", views.qr, name="qr"),
]
