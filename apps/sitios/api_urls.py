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
    path(
        "planos/<int:pk>/imagen/",
        api_views.PlanoImagenView.as_view(),
        name="plano-imagen",
    ),
    path("me/puntos/", api_views.MisPuntosView.as_view(), name="mis-puntos"),
]
