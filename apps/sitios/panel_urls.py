"""Rutas del panel de Sitios."""

from django.urls import path

from . import panel_views as vistas

app_name = "sitios"

urlpatterns = [
    path("", vistas.SitioListado.as_view(), name="listado"),
    path("nuevo/", vistas.SitioAlta.as_view(), name="alta"),
    path("<int:pk>/", vistas.SitioFicha.as_view(), name="ficha"),
    path("<int:pk>/editar/", vistas.SitioEdicion.as_view(), name="editar"),
    path("<int:pk>/qr.png", vistas.qr_png, name="qr_png"),
    path("<int:pk>/regenerar-qr/", vistas.RegenerarQR.as_view(), name="regenerar_qr"),
]
