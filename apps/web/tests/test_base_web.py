"""La plantilla base: barra, menú móvil, botón de WhatsApp y pie."""

import re

from django.template.loader import render_to_string
from django.test import TestCase

from apps.web.models import Configuracion, Servicio


class BaseWebTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Configuracion.objects.all().delete()
        Configuracion.objects.create(
            razon_social="MAControl S.A.",
            telefono="0221 555-1234",
            telefono_internacional="+5492215551234",
            telefono_2="02241 44-5566",
            telefono_2_internacional="+5492241445566",
            whatsapp="+54 9 2215551234",
            cuit="30-12345678-9",
            habilitacion="Habilitación N.º 123",
            director_tecnico="Ing. Fulano",
            direcciones=[
                {"localidad": "Castelli", "direccion": "Saavedra 555",
                 "provincia": "Buenos Aires"},
            ],
            redes=[{"nombre": "Instagram", "url": "https://instagram.com/x"}],
        )  # fmt: skip
        Servicio.objects.create(
            nombre="Servicio de prueba", slug="servicio-prueba", titulo_seo="t",
            resumen="r", problema="p", publicado=True,
        )  # fmt: skip

    def test_marca_pagina_actual(self):
        html = self.client.get("/empresa/").content.decode()
        marcados = re.findall(r'<a [^>]*aria-current="page"[^>]*>([^<]*)</a>', html)
        self.assertIn("Empresa", marcados)
        self.assertNotIn("Contacto", marcados)
        self.assertIn("nav-actual", html)
        servicio = self.client.get("/servicio/servicio-prueba/").content.decode()
        self.assertRegex(servicio, r'<a [^>]*aria-current="page"[^>]*>Servicios</a>')

    def test_whatsapp_flotante_solo_con_numero(self):
        self.assertContains(self.client.get("/"), 'class="whatsapp-flotante"')
        Configuracion.objects.update(whatsapp="")
        self.assertNotContains(self.client.get("/"), "whatsapp-flotante")

    def test_pie_trae_cuit_segundo_telefono_y_copyright(self):
        html = self.client.get("/").content.decode()
        self.assertIn("CUIT 30-12345678-9", html)
        self.assertIn('href="tel:+5492241445566"', html)
        self.assertRegex(html, r"© \d{4} MAControl S\.A\.")
        self.assertIn("Habilitación N.º 123", html)
        self.assertIn("Ing. Fulano", html)
        self.assertIn("https://instagram.com/x", html)

    def test_telefono_movil_con_aria_label(self):
        html = self.client.get("/").content.decode()
        self.assertIn('aria-label="Llamar al 0221 555-1234"', html)
        self.assertIn("nav-telefono-icono", html)

    def test_direccion_enlaza_a_maps(self):
        html = self.client.get("/").content.decode()
        self.assertRegex(
            html, r'href="https://www\.google\.com/maps/search/[^"]*Saavedra[^"]*"'
        )
        self.assertIn('rel="noopener"', html)

    def test_desplegable_lista_los_servicios(self):
        html = self.client.get("/").content.decode()
        panel = re.search(
            r'class="nav-desplegable-panel">(.*?)</div>', html, re.S
        ).group(1)
        self.assertIn('href="/servicio/servicio-prueba/"', panel)
        # El desplegable es solo HTML y CSS: los únicos <script> admitidos son el de la
        # portada (por `src`) y el bloque de datos JSON-LD del inicio (no se ejecuta).
        self.assertEqual(
            [
                s
                for s in re.findall(r"<script\b[^>]*>", html)
                if s != '<script type="application/ld+json">'
            ],
            ['<script src="/static/js/portada.js" defer>'],
        )

    def test_incluye_iconos(self):
        html = render_to_string("web/base_web.html")
        self.assertIn('rel="manifest"', html)
        self.assertIn("apple-touch-icon", html)
