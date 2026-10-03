"""Rutas de la API v1."""

from django.urls import include, path

from . import views

app_name = "api"

urlpatterns = [
    path("", views.RaizView.as_view(), name="raiz"),
    path("auth/token/", views.ObtenerToken.as_view(), name="token"),
    path("auth/token/refresh/", views.RenovarToken.as_view(), name="token_refresh"),
    path("sitios/", include("apps.sitios.api_urls")),
    path("clientes/", include("apps.clientes.api_urls")),
    path("servicios/", include("apps.servicios.api_urls")),
    path("proyectos/", include("apps.proyectos.api_urls")),
    path("productos/", include("apps.productos.api_urls")),
    path("visitas/", include("apps.visitas.api_urls")),
    path("informes/", include("apps.informes.api_urls")),
    path("web/", include("apps.web.api_urls")),
]
