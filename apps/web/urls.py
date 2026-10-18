"""Rutas del sitio público."""

from django.urls import path

from . import views

app_name = "web"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("servicio/<slug:slug>/", views.servicio, name="servicio"),
    path("empresa/", views.empresa, name="empresa"),
    path("contacto/", views.contacto, name="contacto"),
    path("q/<uuid:codigo>/", views.qr, name="qr"),
    path("sitemap.xml", views.sitemap, name="sitemap"),
    path("robots.txt", views.robots, name="robots"),
    path("media/<path:ruta>", views.media_publica, name="media"),
]
