import shutil
import struct
import tempfile
from io import BytesIO
from unittest import mock

from django.core.exceptions import ValidationError
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

    def test_exif_corrupto_no_impide_guardar(self):
        datos = _bytes(Image.new("RGB", (2000, 1000), "red"), "JPEG")
        for error in (struct.error("exif roto"), SyntaxError("exif roto")):
            with self.subTest(error=type(error).__name__):
                with mock.patch(
                    "apps.visitas.imagenes.ImageOps.exif_transpose",
                    side_effect=error,
                ):
                    foto = Foto.objects.create(
                        visita=self.visita,
                        imagen=SimpleUploadedFile(
                            "foto.jpg", datos, content_type="image/jpeg"
                        ),
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

    def test_rechaza_imagen_con_demasiados_pixeles(self):
        datos = _bytes(Image.new("L", (8000, 6000)), "PNG")
        with self.assertRaises(ValidationError):
            Foto.objects.create(
                visita=self.visita,
                imagen=SimpleUploadedFile(
                    "grande.png", datos, content_type="image/png"
                ),
            )
        self.assertEqual(Foto.objects.count(), 0)

    def test_quita_comentario_del_jpeg(self):
        datos = _bytes(Image.new("RGB", (100, 80), "green"), "JPEG", comment=b"SECRETO")
        self.assertIn(b"SECRETO", datos)
        foto = Foto.objects.create(
            visita=self.visita,
            imagen=SimpleUploadedFile("foto.jpg", datos, content_type="image/jpeg"),
        )
        with open(foto.imagen.path, "rb") as guardada:
            self.assertNotIn(b"SECRETO", guardada.read())

    def test_archivo_que_no_es_imagen_lanza_validation_error(self):
        with self.assertRaises(ValidationError):
            Foto.objects.create(
                visita=self.visita,
                imagen=SimpleUploadedFile(
                    "falso.jpg", b"esto no es una imagen", content_type="image/jpeg"
                ),
            )
        self.assertEqual(Foto.objects.count(), 0)
