import re

from django.conf import settings
from django.contrib.staticfiles import finders
from django.template.loader import render_to_string
from django.test import SimpleTestCase


class BaseTemplateTests(SimpleTestCase):
    def test_base_define_tokens_de_ambos_temas(self):
        html = render_to_string("base.html")
        self.assertIn('[data-tema="oscuro"]', html)
        self.assertIn('[data-tema="claro"]', html)
        self.assertIn("#0f1417", html)
        self.assertIn("#f4f3ef", html)
        self.assertIn("--brand: #ffc600", html)
        self.assertIn('<html lang="es" data-tema="oscuro">', html)
        self.assertIn("img/logo.png", html)

    def test_base_tema_por_defecto_es_oscuro(self):
        html = render_to_string("base.html")
        self.assertIn('<html lang="es" data-tema="oscuro">', html)

    def test_base_no_carga_fuentes_de_terceros(self):
        html = render_to_string("base.html")
        self.assertNotIn("fonts.googleapis.com", html)
        self.assertNotIn("fonts.gstatic.com", html)

    def test_fuentes_referenciadas_existen(self):
        html = render_to_string("base.html")
        bloques = re.findall(r"@font-face\s*\{[^}]*\}", html)
        urls = [u for b in bloques for u in re.findall(r'url\("([^"]+)"\)', b)]
        self.assertGreaterEqual(len(urls), 7)
        for url in urls:
            ruta = url.removeprefix(settings.STATIC_URL)
            self.assertIsNotNone(finders.find(ruta), url)
