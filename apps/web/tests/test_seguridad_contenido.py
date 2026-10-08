"""Seguridad del contenido del sitio: imágenes subidas y redes sociales."""

import json
import os
import shutil
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.accounts.models import User
from apps.servicios.models import TipoServicio
from apps.web.models import ClienteDestacado, Configuracion, PaginaServicio

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

    def test_nombre_uuid_y_reemplazo_borra_el_anterior(self):
        def subir(url, nombre):
            return SimpleUploadedFile(nombre, imagen_bytes("PNG"), "image/png")

        self.client.post(
            reverse("panel:web:cliente_alta"),
            {"nombre": "Uno", "orden": 0, "logo": subir(None, "Mi Logo Original.png")},
        )
        cliente = ClienteDestacado.objects.get(nombre="Uno")
        primero = cliente.logo.name
        self.assertRegex(primero, r"^clientes/[0-9a-f]{32}\.png$")
        self.assertTrue(os.path.exists(cliente.logo.path))
        self.client.post(
            reverse("panel:web:cliente_editar", args=[cliente.pk]),
            {"nombre": "Uno", "orden": 0, "logo": subir(None, "otro.png")},
        )
        cliente.refresh_from_db()
        self.assertNotEqual(cliente.logo.name, primero)
        self.assertFalse(cliente.logo.storage.exists(primero))
        self.assertTrue(os.path.exists(cliente.logo.path))


class RedesTests(BaseSubidas):
    def test_redes_rechaza_url_que_no_es_https(self):
        url = reverse("panel:web:configuracion")
        base = {
            "razon_social": "MAControl S.A.",
            "telefono": "02241 49 6047",
            "direcciones": "[]",
        }
        for mala in ("javascript:alert(1)", "http://sitio.com", "ftp://x.com/a"):
            redes = json.dumps([{"nombre": "Red", "url": mala}])
            respuesta = self.client.post(url, {**base, "redes": redes})
            self.assertIn("redes", respuesta.context["form"].errors, mala)
        buena = json.dumps([{"nombre": "Red", "url": "https://sitio.com/perfil"}])
        self.client.post(url, {**base, "redes": buena})
        self.assertEqual(Configuracion.obtener().redes[0]["nombre"], "Red")
