"""Seguridad del contenido del sitio: imágenes subidas."""

import shutil
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.accounts.models import User
from apps.servicios.models import TipoServicio
from apps.web.models import ClienteDestacado, PaginaServicio

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="web-media-")


def imagen_bytes(formato, modo="RGB", exif=False, **extra):
    imagen = Image.new(modo, (20, 10), (200, 30, 30, 128)[: len(modo)])
    salida = BytesIO()
    kwargs = dict(extra)
    if exif:
        datos = Image.Exif()
        datos[0x010F] = "Camara"
        datos[0x8825] = {1: "S", 2: (34.0, 36.0, 0.0)}
        kwargs["exif"] = datos
    imagen.save(salida, format=formato, **kwargs)
    return salida.getvalue()


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class BaseSubidas(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.addClassCleanup(shutil.rmtree, MEDIA_TEMPORAL, ignore_errors=True)

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin-seg", password="x", rol=User.Rol.ADMINISTRADOR
        )
        self.client.force_login(self.admin)


class ImagenesSubidasTests(BaseSubidas):
    def datos_pagina(self, **extra):
        return {
            "titulo_seo": "Roedores",
            "resumen": "r",
            "problema": "p",
            "adicional": "",
            "metodos": "[]",
            "faq": "[]",
            "publicado": "on",
            **extra,
        }

    def pagina(self):
        tipo = TipoServicio.objects.create(nombre="Roedores", slug="roedores-seg")
        return PaginaServicio.objects.create(
            tipo=tipo, titulo_seo="Roedores", resumen="r", problema="p"
        )

    def test_portada_subida_pierde_exif_y_gps(self):
        pagina = self.pagina()
        crudo = imagen_bytes("JPEG", exif=True)
        self.assertIn(0x8825, Image.open(BytesIO(crudo)).getexif())
        archivo = SimpleUploadedFile("foto.jpg", crudo, "image/jpeg")
        url = reverse("panel:web:pagina_editar", args=[pagina.pk])
        self.client.post(url, self.datos_pagina(imagen_portada=archivo))
        pagina.refresh_from_db()
        with Image.open(pagina.imagen_portada.path) as guardada:
            self.assertEqual(guardada.format, "JPEG")
            self.assertEqual(len(guardada.getexif()), 0)
            self.assertNotIn("exif", guardada.info)

    def test_logo_conserva_transparencia_y_pierde_metadatos(self):
        crudo = imagen_bytes("PNG", "RGBA", exif=True)
        archivo = SimpleUploadedFile("logo.png", crudo, "image/png")
        self.client.post(
            reverse("panel:web:cliente_alta"),
            {"nombre": "ACME", "orden": 0, "logo": archivo},
        )
        cliente = ClienteDestacado.objects.get(nombre="ACME")
        with Image.open(cliente.logo.path) as guardado:
            self.assertEqual(guardado.format, "PNG")
            self.assertEqual(guardado.mode, "RGBA")
            self.assertEqual(guardado.getpixel((0, 0))[3], 128)
            self.assertEqual(len(guardado.getexif()), 0)
            self.assertNotIn("exif", guardado.info)

    def test_rechaza_gif_con_extension_png(self):
        gif = SimpleUploadedFile("logo.png", imagen_bytes("GIF", "P"), "image/png")
        respuesta = self.client.post(
            reverse("panel:web:cliente_alta"),
            {"nombre": "GIF", "orden": 0, "logo": gif},
        )
        self.assertIn("logo", respuesta.context["form"].errors)
        self.assertFalse(ClienteDestacado.objects.filter(nombre="GIF").exists())
