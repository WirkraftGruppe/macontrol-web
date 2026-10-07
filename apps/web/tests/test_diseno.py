"""La base visual de la web: web.css, sin recursos externos y con la CSP intacta."""

import re

from django.template.loader import render_to_string
from django.test import TestCase


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
