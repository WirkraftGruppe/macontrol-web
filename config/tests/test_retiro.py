"""El proyecto quedó sin panel, API, apps de dominio ni accounts."""

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

RETIRADAS = (
    "accounts",
    "clientes",
    "sitios",
    "proyectos",
    "visitas",
    "productos",
    "informes",
    "panel",
    "api",
    "rest_framework",
    "drf_spectacular",
    "simple_history",
)


class RetiroTests(TestCase):
    def test_apps_retiradas_no_estan_instaladas(self):
        etiquetas = {config.label for config in apps.get_app_configs()}
        for etiqueta in RETIRADAS:
            with self.subTest(app=etiqueta):
                self.assertNotIn(etiqueta, etiquetas)

    def test_panel_y_api_dan_404(self):
        for ruta in ("/panel/", "/panel/ingresar/", "/api/v1/", "/api/v1/token/"):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 404)

    def test_usuario_es_el_de_django(self):
        self.assertEqual(settings.AUTH_USER_MODEL, "auth.User")
        self.assertEqual(get_user_model()._meta.label, "auth.User")
