from django.test import SimpleTestCase
from PIL import ImageFont

from apps.sitios import qr


class QrTests(SimpleTestCase):
    def test_dibuja_letras_acentuadas(self):
        """La fuente del QR tiene glifo propio para "ó", no el de un faltante."""
        fuente = ImageFont.truetype(qr.RUTA_FUENTE, 22)

        def mapa(letra):
            mascara = fuente.getmask(letra)
            return mascara.size, bytes(mascara)

        self.assertNotEqual(mapa("ó"), mapa("o"))
        self.assertNotEqual(mapa("ó"), mapa("中"))
