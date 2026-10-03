"""Tests de rutas de la app Clientes."""

from django.test import SimpleTestCase

from apps.clientes import api_urls, panel_urls


class RutasClientesTests(SimpleTestCase):
    """Tests que verifican la estructura de rutas de Clientes."""

    def test_routers_de_clientes_estan_vacios(self):
        """
        Comprueba que los routers de Clientes (API y panel) tengan el
        nombre correcto y estén aún vacíos.
        """
        # Verificar api_urls
        self.assertEqual(api_urls.app_name, "clientes")
        self.assertEqual(api_urls.urlpatterns, [])

        # Verificar panel_urls
        self.assertEqual(panel_urls.app_name, "clientes")
        self.assertEqual(panel_urls.urlpatterns, [])
