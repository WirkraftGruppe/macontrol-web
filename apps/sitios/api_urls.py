"""Rutas de API de Sitios (montadas en la raíz de `/api/v1/`)."""

from django.urls import path

from . import api_views

app_name = "sitios"

urlpatterns = [
    path(
        "qr/<uuid:codigo>/resolver/",
        api_views.ResolverQRView.as_view(),
        name="qr-resolver",
    ),
]
