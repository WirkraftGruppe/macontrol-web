"""La base visual de la web: web.css, sin recursos externos y con la CSP intacta."""

import re

from django.conf import settings
from django.template.loader import render_to_string
from django.test import TestCase
from PIL import Image


class DisenoWebTests(TestCase):
    def test_home_carga_web_css_sin_recursos_externos_ni_unsafe_inline(self):
        respuesta = self.client.get("/")
        self.assertNotIn("unsafe-inline", respuesta["Content-Security-Policy"])
        html = respuesta.content.decode()
        self.assertIn("css/web.css", html)
        self.assertNotRegex(
            html, r"https?://(?!www\.w3\.org)[^\"'\s]*\.(css|js|woff2?)"
        )
        self.assertNotIn("fonts.googleapis", html)
        self.assertNotIn("<script", html)
        self.assertNotIn("style=", html)
        for url in re.findall(r'(?:src|href)="(https?://[^"]+)"', html):
            self.assertNotIn("/static/", url)
            self.assertNotRegex(url, r"\.(css|js|woff2?|png|webp|jpe?g)$")

    def test_base_web_renderiza_sin_contexto(self):
        html = render_to_string("web/base_web.html")
        self.assertIn("css/web.css", html)
        self.assertIn('<main id="contenido">', html)

    def test_tarjetas_de_seccion_amarilla_usan_texto_claro_sobre_fondo_oscuro(self):
        css = (settings.BASE_DIR / "static/css/web.css").read_text(encoding="utf-8")
        bloques = [
            cuerpo
            for selector, cuerpo in re.findall(r"([^{}]+)\{([^{}]*)\}", css)
            if ".seccion-amarilla .tarjeta" in selector
        ]
        self.assertTrue(bloques, "falta la regla .seccion-amarilla .tarjeta")
        declaraciones = " ".join(bloques)
        self.assertRegex(declaraciones, r"background:\s*var\(--bg\)")
        self.assertRegex(declaraciones, r"(?<![-\w])color:\s*var\(--text\)")

    def test_logo_declara_width_y_height(self):
        html = render_to_string("web/base_web.html")
        etiqueta = re.search(r"<img[^>]*logo\.png[^>]*>", html).group(0)
        ancho = re.search(r'\bwidth="(\d+)"', etiqueta)
        alto = re.search(r'\bheight="(\d+)"', etiqueta)
        self.assertTrue(ancho and alto, "el logo necesita width y height")
        with Image.open(settings.BASE_DIR / "static/img/logo.png") as logo:
            real_ancho, real_alto = logo.size
        self.assertAlmostEqual(
            int(ancho.group(1)) / int(alto.group(1)), real_ancho / real_alto, places=1
        )
