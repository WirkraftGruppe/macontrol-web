"""Rutas del panel de gestión."""

from django.urls import include, path

from . import views

app_name = "panel"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("sitios/", include("apps.sitios.panel_urls")),
    path("clientes/", include("apps.clientes.panel_urls")),
    path("servicios/", include("apps.servicios.panel_urls")),
    path("proyectos/", include("apps.proyectos.panel_urls")),
    path("productos/", include("apps.productos.panel_urls")),
    path("visitas/", include("apps.visitas.panel_urls")),
    path("informes/", include("apps.informes.panel_urls")),
    path("web/", include("apps.web.panel_urls")),
]
