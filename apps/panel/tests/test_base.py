"""La plantilla base del panel usa el tema claro."""

from django.template.loader import render_to_string
from django.test import SimpleTestCase


class PanelBaseTests(SimpleTestCase):
    def test_panel_base_usa_tema_claro(self):
        html = render_to_string("panel/base.html")
        self.assertIn('<html lang="es" data-tema="claro">', html)
