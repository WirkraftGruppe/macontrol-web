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
    path(
        "favicon.ico",
        views.archivo_raiz,
        {"nombre": "favicon.ico"},
        name="favicon",
    ),
    path(
        "apple-touch-icon.png",
        views.archivo_raiz,
        {"nombre": "apple-touch-icon.png"},
        name="apple_touch_icon",
    ),
    path("site.webmanifest", views.manifiesto, name="manifiesto"),
    path("media/<path:ruta>", views.media_publica, name="media"),
]
