import shutil
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from apps.visitas.models import Foto

from .test_models import crear_visita

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="macontrol-test-")


def _bytes(imagen, formato, **opciones):
    salida = BytesIO()
    imagen.save(salida, format=formato, **opciones)
    return salida.getvalue()


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class FotoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.visita = crear_visita()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def test_redimensiona_y_quita_exif(self):
        exif = Image.Exif()
        exif[0x010F] = "Camara"
        exif[0x8825] = {1: "S", 2: (34.0, 36.0, 0.0), 3: "W", 4: (58.0, 22.0, 0.0)}
        datos = _bytes(Image.new("RGB", (3000, 2000), "red"), "JPEG", exif=exif)
        self.assertTrue(Image.open(BytesIO(datos)).getexif())
        foto = Foto.objects.create(
            visita=self.visita,
            imagen=SimpleUploadedFile("foto.jpg", datos, content_type="image/jpeg"),
        )
        with Image.open(foto.imagen.path) as guardada:
            self.assertEqual(max(guardada.size), 1600)
            self.assertEqual(len(guardada.getexif()), 0)

    def test_png_se_guarda_como_jpeg(self):
        datos = _bytes(Image.new("RGBA", (100, 80), "blue"), "PNG")
        foto = Foto.objects.create(
            visita=self.visita,
            imagen=SimpleUploadedFile(
                "casa de Perez.png", datos, content_type="image/png"
            ),
        )
        with Image.open(foto.imagen.path) as guardada:
            self.assertEqual(guardada.format, "JPEG")
        self.assertNotIn("Perez", foto.imagen.name)
