"""Rutas raíz del proyecto."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("panel/", include("apps.panel.urls")),
    path("api/v1/", include("apps.api.urls")),
    path("", include("apps.web.urls")),
]
