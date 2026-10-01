"""Rutas de la API v1."""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.raiz, name="raiz"),
]
