"""Tests del admin del contenido: vista previa, imágenes, redes y textos."""

import json
import shutil
import tempfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from apps.web.models import Configuracion, Servicio

CLAVE = "clave-larga-123"


def crear_servicio(**extra):
    datos = {
        "nombre": "Servicio oculto",
        "slug": "servicio-oculto",
        "titulo_seo": "Servicio oculto",
        "resumen": "Resumen del servicio oculto",
        "problema": "Problema que resuelve",
        "publicado": False,
    }
    return Servicio.objects.create(**{**datos, **extra})


def jpeg_con_exif():
    """JPEG de prueba con un EXIF que incluye un puntero a GPS."""
    exif = Image.Exif()
    exif[0x010F] = "CamaraSecreta"
    exif[0x8825] = {1: "S", 2: (34.0, 36.0, 0.0), 3: "W", 4: (58.0, 22.0, 0.0)}
    salida = BytesIO()
    Image.new("RGB", (40, 30), "green").save(salida, "JPEG", exif=exif)
    return salida.getvalue()


class AdminBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superusuario = get_user_model().objects.create_superuser(
            "root", password=CLAVE
        )

    def setUp(self):
        self.client.force_login(self.superusuario)


class VistaPreviaTests(AdminBase):
    def test_superusuario_ve_servicio_no_publicado(self):
        servicio = crear_servicio()
        self.assertEqual(self.client.get(servicio.get_absolute_url()).status_code, 404)
        r = self.client.get(f"/admin/web/servicio/{servicio.pk}/vista-previa/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Servicio oculto")
        self.assertEqual(r["X-Robots-Tag"], "noindex")

    def test_anonimo_redirige_al_login_del_admin(self):
        servicio = crear_servicio()
        self.client.logout()
        r = self.client.get(f"/admin/web/servicio/{servicio.pk}/vista-previa/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/admin/login/", r["Location"])

    def test_staff_no_superusuario_no_accede(self):
        servicio = crear_servicio()
        staff = get_user_model().objects.create_user(
            "jefe", password=CLAVE, is_staff=True
        )
        self.client.force_login(staff)
        r = self.client.get(f"/admin/web/servicio/{servicio.pk}/vista-previa/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/admin/login/", r["Location"])


class AdminImagenesTests(AdminBase):
    def setUp(self):
        super().setUp()
        media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)
        configuracion = override_settings(MEDIA_ROOT=media)
        configuracion.enable()
        self.addCleanup(configuracion.disable)

    def test_foto_subida_pierde_exif(self):
        original = jpeg_con_exif()
        self.assertIn(b"CamaraSecreta", original)
        datos = {
            "nombre": "Con foto",
            "slug": "con-foto",
            "titulo_seo": "Con foto",
            "resumen": "Resumen",
            "problema": "Problema",
            "orden": 1,
            "foto": SimpleUploadedFile("foto.jpg", original, "image/jpeg"),
        }
        r = self.client.post("/admin/web/servicio/add/", datos)
        self.assertEqual(r.status_code, 302, getattr(r, "context", None))
        guardada = Servicio.objects.get(slug="con-foto").foto
        with guardada.open("rb") as archivo:
            contenido = archivo.read()
        self.assertNotIn(b"CamaraSecreta", contenido)
        with Image.open(BytesIO(contenido)) as imagen:
            self.assertEqual(len(imagen.getexif()), 0)


class AdminConfiguracionTests(AdminBase):
    def datos(self, **extra):
        base = {
            "razon_social": "MAControl S.A.",
            "eslogan": "",
            "presentacion": "",
            "telefono": "",
            "whatsapp": "",
            "correo": "",
            "horario": "",
            "habilitacion": "",
            "ley": "",
            "director_tecnico": "",
            "direcciones": "[]",
            "redes": "[]",
        }
        return {**base, **extra}

    def test_red_con_javascript_se_rechaza(self):
        Configuracion.obtener()
        redes = json.dumps([{"nombre": "Mala", "url": "javascript:alert(1)"}])
        r = self.client.post(
            "/admin/web/configuracion/1/change/", self.datos(redes=redes)
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "debe ser una dirección https válida")
        self.assertEqual(Configuracion.obtener().redes, [])

    def test_datos_legales_se_editan(self):
        Configuracion.obtener()
        datos = self.datos(
            habilitacion="Habilitación 123",
            ley="Ley de prueba",
            director_tecnico="Ing. Prueba",
        )
        r = self.client.post("/admin/web/configuracion/1/change/", datos)
        self.assertEqual(r.status_code, 302)
        config = Configuracion.obtener()
        self.assertEqual(config.habilitacion, "Habilitación 123")
        self.assertEqual(config.ley, "Ley de prueba")
        self.assertEqual(config.director_tecnico, "Ing. Prueba")


class AdminEspanolTests(AdminBase):
    def test_listado_y_formulario_en_espanol(self):
        servicio = crear_servicio()
        listado = self.client.get("/admin/web/servicio/")
        self.assertContains(listado, "Servicios")
        self.assertContains(listado, "Publicado")
        formulario = self.client.get(f"/admin/web/servicio/{servicio.pk}/change/")
        self.assertContains(formulario, "Vista previa")
        self.assertContains(formulario, "Portada")
        self.assertContains(formulario, "Preguntas frecuentes")
        Configuracion.obtener()
        config = self.client.get("/admin/web/configuracion/1/change/")
        for texto in ("Contacto", "Datos legales", "Redes y direcciones"):
            self.assertContains(config, texto)
