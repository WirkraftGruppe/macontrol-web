"""Rutas de Productos: comprobación de que están vacías en T5."""

from django.test import SimpleTestCase

from apps.productos import api_urls, panel_urls


class RutasProductosTests(SimpleTestCase):
    """Pruebas de que los routers de Productos están vacíos."""

    def test_routers_de_productos_estan_vacios(self):
        """Comprueba que api_urls y panel_urls tienen app_name correcto y sin rutas."""
        self.assertEqual(api_urls.app_name, "productos")
        self.assertEqual(api_urls.urlpatterns, [])

        self.assertEqual(panel_urls.app_name, "productos")
        self.assertEqual(panel_urls.urlpatterns, [])
