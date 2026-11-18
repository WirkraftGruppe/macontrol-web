"""El reprocesado de imágenes no depende del estado global de `warnings`."""

import warnings
from io import BytesIO
from unittest import mock

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image

from apps.web.imagenes import reprocesar_imagen


class PixelesTests(SimpleTestCase):
    def _png(self, ancho, alto):
        buffer = BytesIO()
        Image.new("RGB", (ancho, alto), "white").save(buffer, format="PNG")
        return SimpleUploadedFile("a.png", buffer.getvalue(), "image/png")

    def test_rechaza_exceso_de_pixeles_sin_depender_de_los_filtros_de_avisos(self):
        # Con `simplefilter` anulado (otro hilo lo pisó) el aviso de Pillow no
        # se convertiría en error: el tope debe aplicarse leyendo la cabecera.
        with (
            mock.patch.object(Image, "MAX_IMAGE_PIXELS", 100),
            mock.patch.object(warnings, "simplefilter", lambda *a, **k: None),
            self.assertRaises(ValidationError),
        ):
            reprocesar_imagen(self._png(11, 11), formato_salida="PNG")

    def test_imagen_dentro_del_tope_se_reprocesa(self):
        with mock.patch.object(Image, "MAX_IMAGE_PIXELS", 400):
            salida = reprocesar_imagen(self._png(11, 11), formato_salida="PNG")
        self.assertTrue(salida.read())
