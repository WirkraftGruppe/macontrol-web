"""Tests del admin del contenido: vista previa, imágenes, redes y textos."""

import json
import re
import shutil
import tempfile
from io import BytesIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image, PngImagePlugin

from apps.web.imagenes import reprocesar_imagen
from apps.web.models import ClienteDestacado, Configuracion, Servicio
from apps.web.validators import TAMANO_MAXIMO_IMAGEN

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


def imagen_bytes(formato="JPEG", tamano=(40, 30), color="green"):
    salida = BytesIO()
    Image.new("RGB", tamano, color).save(salida, formato)
    return salida.getvalue()


def datos_servicio(**extra):
    base = {
        "nombre": "Con foto",
        "slug": "con-foto",
        "titulo_seo": "Con foto",
        "resumen": "Resumen",
        "problema": "Problema",
        "orden": 1,
    }
    return {**base, **extra}


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

    def test_pk_inexistente_da_404(self):
        r = self.client.get("/admin/web/servicio/99999/vista-previa/")
        self.assertEqual(r.status_code, 404)

    def test_vista_previa_y_publica_comparten_contexto(self):
        servicio = crear_servicio(publicado=True, sectores=["hoteleria"])
        crear_servicio(nombre="Otro", slug="otro", publicado=True)
        publica = self.client.get(servicio.get_absolute_url())
        previa = self.client.get(f"/admin/web/servicio/{servicio.pk}/vista-previa/")
        for clave in ("pagina", "portada", "sectores", "seo"):
            self.assertEqual(publica.context[clave], previa.context[clave], clave)
        self.assertEqual(
            list(publica.context["relacionados"]),
            list(previa.context["relacionados"]),
        )
        self.assertEqual(publica.context["sectores"], ["Hotelería"])

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

    def _servicio_con_foto(self):
        foto = SimpleUploadedFile("a.jpg", imagen_bytes(), "image/jpeg")
        r = self.client.post("/admin/web/servicio/add/", datos_servicio(foto=foto))
        self.assertEqual(r.status_code, 302)
        return Servicio.objects.get(slug="con-foto")

    def test_reemplazar_foto_borra_la_anterior_al_confirmar(self):
        servicio = self._servicio_con_foto()
        anterior = servicio.foto.name
        nueva = SimpleUploadedFile("b.jpg", imagen_bytes(color="red"), "image/jpeg")
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            r = self.client.post(
                f"/admin/web/servicio/{servicio.pk}/change/",
                datos_servicio(foto=nueva),
            )
            self.assertEqual(r.status_code, 302)
            self.assertTrue(servicio.foto.storage.exists(anterior))
        servicio.refresh_from_db()
        self.assertEqual(len(callbacks), 1)
        self.assertNotEqual(servicio.foto.name, anterior)
        self.assertFalse(servicio.foto.storage.exists(anterior))
        self.assertTrue(servicio.foto.storage.exists(servicio.foto.name))

    def test_quitar_foto_borra_el_archivo(self):
        servicio = self._servicio_con_foto()
        anterior = servicio.foto.name
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(
                f"/admin/web/servicio/{servicio.pk}/change/",
                datos_servicio(**{"foto-clear": "on"}),
            )
        servicio.refresh_from_db()
        self.assertFalse(servicio.foto)
        self.assertFalse(servicio.foto.storage.exists(anterior))

    def test_borrar_servicio_borra_su_foto(self):
        servicio = self._servicio_con_foto()
        nombre = servicio.foto.name
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(
                f"/admin/web/servicio/{servicio.pk}/delete/", {"post": "yes"}
            )
            self.assertEqual(r.status_code, 302)
            self.assertTrue(servicio.foto.storage.exists(nombre))
        self.assertFalse(servicio.foto.storage.exists(nombre))

    def test_borrar_clientes_en_lote_borra_sus_logos(self):
        cliente = ClienteDestacado(nombre="Con logo")
        cliente.logo.save("l.png", ContentFile(imagen_bytes("PNG")))
        nombre = cliente.logo.name
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(
                "/admin/web/clientedestacado/",
                {
                    "action": "delete_selected",
                    "_selected_action": [cliente.pk],
                    "post": "yes",
                },
            )
            self.assertEqual(r.status_code, 302)
        self.assertFalse(ClienteDestacado.objects.exists())
        self.assertFalse(cliente.logo.storage.exists(nombre))

    def test_gif_renombrado_se_rechaza(self):
        gif = imagen_bytes("GIF")
        datos = datos_servicio(foto=SimpleUploadedFile("foto.jpg", gif, "image/jpeg"))
        r = self.client.post("/admin/web/servicio/add/", datos)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "no es una imagen válida")
        self.assertFalse(Servicio.objects.exists())

    def test_archivo_mayor_al_tope_se_rechaza_sin_abrirlo(self):
        grande = ContentFile(b"0" * (TAMANO_MAXIMO_IMAGEN + 1), name="x.jpg")
        with mock.patch("apps.web.imagenes.Image.open") as abrir:
            with self.assertRaises(ValidationError):
                reprocesar_imagen(grande, formato_salida="JPEG")
        abrir.assert_not_called()

    def test_logo_de_cliente_conserva_alfa_sin_metadatos_y_nombre_uuid(self):
        meta = PngImagePlugin.PngInfo()
        meta.add_text("Secreto", "dato-privado")
        salida = BytesIO()
        Image.new("RGBA", (20, 10), (255, 0, 0, 0)).save(salida, "PNG", pnginfo=meta)
        self.assertIn(b"dato-privado", salida.getvalue())
        datos = {
            "nombre": "Con alfa",
            "orden": 1,
            "logo": SimpleUploadedFile("mi logo.PNG", salida.getvalue(), "image/png"),
        }
        r = self.client.post("/admin/web/clientedestacado/add/", datos)
        self.assertEqual(r.status_code, 302, getattr(r, "context", None))
        logo = ClienteDestacado.objects.get(nombre="Con alfa").logo
        self.assertRegex(logo.name, r"^clientes/[0-9a-f]{32}\.png$")
        with logo.open("rb") as archivo:
            contenido = archivo.read()
        self.assertNotIn(b"dato-privado", contenido)
        with Image.open(BytesIO(contenido)) as imagen:
            self.assertEqual(imagen.mode, "RGBA")
            self.assertEqual(imagen.getpixel((0, 0))[3], 0)


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
        Configuracion().save()
        redes = json.dumps([{"nombre": "Mala", "url": "javascript:alert(1)"}])
        r = self.client.post(
            "/admin/web/configuracion/1/change/", self.datos(redes=redes)
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "debe ser una dirección https válida")
        self.assertEqual(Configuracion.obtener().redes, [])

    def test_red_http_o_con_credenciales_se_rechaza(self):
        Configuracion().save()
        for url in ("http://ejemplo.com/perfil", "https://usuario:clave@ejemplo.com/"):
            redes = json.dumps([{"nombre": "Mala", "url": url}])
            r = self.client.post(
                "/admin/web/configuracion/1/change/", self.datos(redes=redes)
            )
            self.assertEqual(r.status_code, 200, url)
            self.assertContains(r, "debe ser una dirección https válida")
        self.assertEqual(Configuracion.obtener().redes, [])

    def test_datos_legales_se_editan(self):
        Configuracion().save()
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
        Configuracion().save()
        config = self.client.get("/admin/web/configuracion/1/change/")
        for texto in ("Contacto", "Datos legales", "Redes y direcciones"):
            self.assertContains(config, texto)

    def test_miniatura_sin_atributo_style(self):
        media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)
        with override_settings(MEDIA_ROOT=media):
            servicio = crear_servicio()
            servicio.foto.save("f.jpg", ContentFile(imagen_bytes(tamano=(400, 100))))
            r = self.client.get(f"/admin/web/servicio/{servicio.pk}/change/")
        etiqueta = re.search(
            rf'<img src="{re.escape(servicio.foto.url)}"[^>]*>', r.text
        )
        self.assertIsNotNone(etiqueta, "no aparece la miniatura")
        self.assertNotIn("style=", etiqueta.group())
        self.assertIn('width="160" height="40"', etiqueta.group())
