"""Rutas del sitio público."""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("q/<uuid:codigo>/", views.qr, name="qr"),
]
