"""Tests de la identidad visual: favicon, iconos, imagen para compartir y parcial."""

import importlib.util
import tempfile
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase
from PIL import Image, ImageChops

STATIC = Path(settings.BASE_DIR) / "static"
PARCIAL = Path(settings.BASE_DIR) / "apps/web/templates/web/_iconos.html"
GENERADOR = Path(settings.BASE_DIR) / "herramientas/generar_identidad.py"


def _cargar_generador():
    spec = importlib.util.spec_from_file_location("generar_identidad", GENERADOR)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class IdentidadTests(SimpleTestCase):
    def test_tamanos_de_los_png(self):
        for nombre, lado in (
            ("apple-touch-icon.png", 180),
            ("icono-192.png", 192),
            ("icono-512.png", 512),
        ):
            with Image.open(STATIC / "img" / nombre) as imagen:
                self.assertEqual(imagen.size, (lado, lado), nombre)

    def test_ico_trae_16_y_32(self):
        with Image.open(STATIC / "favicon.ico") as ico:
            self.assertEqual(sorted(ico.info["sizes"]), [(16, 16), (32, 32)])

    def test_og_es_1200x630(self):
        with Image.open(STATIC / "img" / "og-macontrol.png") as og:
            self.assertEqual(og.size, (1200, 630))

    def test_svg_trae_los_trazos_del_adjunto_b(self):
        svg = (STATIC / "img" / "favicon.svg").read_text(encoding="utf-8")
        self.assertIn('viewBox="0 0 64 64"', svg)
        self.assertIn(
            "M9.5 44 V25 a4 4 0 0 1 4 -4 H24.5 a4 4 0 0 1 4 4 V44 M19 21 V44", svg
        )
        self.assertIn("M57.5 21 H43 a4 4 0 0 0 -4 4 V40 a4 4 0 0 0 4 4 H57.5", svg)
        self.assertEqual(svg.count('stroke-width="6"'), 2)
        self.assertIn('fill="#ffc600"', svg)

    def test_parcial_enlaza_iconos(self):
        html = PARCIAL.read_text(encoding="utf-8")
        for esperado in (
            '<link rel="icon" href="/favicon.ico" sizes="32x32">',
            '<link rel="icon" href="{% static \'img/favicon.svg\' %}"'
            ' type="image/svg+xml">',
            '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
            '<link rel="manifest" href="/site.webmanifest">',
            '<meta name="theme-color" content="#0f1417">',
        ):
            self.assertIn(esperado, html)
        self.assertNotIn("style=", html)
        self.assertNotIn("<script", html)

    def test_generador_reproduce_los_archivos(self):
        """Compara píxeles (no bytes): la compresión de zlib puede variar entre
        versiones de Pillow sin que cambie la imagen."""
        generador = _cargar_generador()
        with tempfile.TemporaryDirectory() as temporal:
            salida = Path(temporal)
            generador.generar(salida)
            generador.generar(salida)  # idempotente
            relativos = [
                "favicon.ico",
                "img/apple-touch-icon.png",
                "img/icono-192.png",
                "img/icono-512.png",
                "img/og-macontrol.png",
            ]
            for relativo in relativos:
                with (
                    Image.open(salida / relativo) as nueva,
                    Image.open(STATIC / relativo) as commiteada,
                ):
                    self.assertEqual(nueva.size, commiteada.size, relativo)
                    diferencia = ImageChops.difference(
                        nueva.convert("RGBA"), commiteada.convert("RGBA")
                    )
                    self.assertIsNone(diferencia.getbbox(), relativo)
