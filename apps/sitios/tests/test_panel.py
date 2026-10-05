from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.clientes.models import Cliente
from apps.sitios import qr
from apps.sitios.models import PuntoControl, Sitio

User = get_user_model()


class SitioPanelTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            "adm", password="clave-segura-123", rol=User.Rol.ADMINISTRADOR
        )
        self.client.force_login(self.admin)
        self.cliente = Cliente.objects.create(razon_social="ACME")
        self.sitio = Sitio.objects.create(cliente=self.cliente, nombre="Planta Ñandú 1")

    def _datos(self, **extra):
        datos = {
            "cliente": self.cliente.pk,
            "nombre": "Depósito Norte",
            "sector": Sitio.Sector.OTRO,
            "latitud": "-35.123456",
            "longitud": "-57.654321",
            "activo": "on",
        }
        datos.update(extra)
        return datos

    def test_descargar_qr_png_con_nombre(self):
        r = self.client.get(reverse("panel:sitios:qr_png", args=[self.sitio.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "image/png")
        self.assertEqual(
            r["Content-Disposition"],
            'attachment; filename="qr-planta-nandu-1.png"',
        )
        self.assertEqual(Image.open(BytesIO(r.content)).format, "PNG")
        self.assertEqual(
            r.content,
            qr.png_qr(self.sitio.puntos.get()),
            "El PNG es el del punto General",
        )

    def test_regenerar_qr_invalida_el_anterior(self):
        url = reverse("panel:sitios:regenerar_qr", args=[self.sitio.pk])
        general = self.sitio.puntos.get()
        anterior = general.qr_codigo
        self.assertEqual(self.client.get(url).status_code, 200)
        general.refresh_from_db()
        self.assertEqual(general.qr_codigo, anterior)
        self.client.post(url)
        general.refresh_from_db()
        self.assertNotEqual(general.qr_codigo, anterior)
        self.assertFalse(PuntoControl.objects.filter(qr_codigo=anterior).exists())

    def test_alta_y_edicion_guardan_lat_lng(self):
        r = self.client.post(reverse("panel:sitios:alta"), self._datos())
        self.assertEqual(r.status_code, 302)
        nuevo = Sitio.objects.get(nombre="Depósito Norte")
        self.assertEqual(nuevo.latitud, Decimal("-35.123456"))
        self.assertEqual(nuevo.longitud, Decimal("-57.654321"))
        self.client.post(
            reverse("panel:sitios:editar", args=[nuevo.pk]),
            self._datos(latitud="-36.5", longitud="-58.25"),
        )
        nuevo.refresh_from_db()
        self.assertEqual(nuevo.latitud, Decimal("-36.5"))
        self.assertEqual(nuevo.longitud, Decimal("-58.25"))

    @override_settings(SITE_URL="https://ejemplo.test")
    def test_contenido_qr_usa_site_url(self):
        general = self.sitio.puntos.get()
        self.assertEqual(
            qr.contenido_qr(general),
            f"https://ejemplo.test/q/{general.qr_codigo}/",
        )

    def test_listado_filtra_y_exige_administrador(self):
        otro = Cliente.objects.create(razon_social="Otra")
        Sitio.objects.create(cliente=otro, nombre="Silo", activo=False)
        url = reverse("panel:sitios:listado")
        r = self.client.get(url, {"cliente": otro.pk, "activo": "0"})
        self.assertContains(r, "Silo")
        self.assertNotContains(r, "Planta")
        self.assertEqual(self.client.get(url, {"q": "Planta"}).status_code, 200)
        self.client.force_login(
            User.objects.create_user("emp", password="clave-segura-123")
        )
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_ficha_muestra_el_qr(self):
        r = self.client.get(reverse("panel:sitios:ficha", args=[self.sitio.pk]))
        self.assertContains(r, reverse("panel:sitios:qr_png", args=[self.sitio.pk]))


class HistorialSitioTests(TestCase):
    def test_notas_y_horario_no_van_al_historial(self):
        modelo = Sitio.history.model
        for campo in ("notas", "horario_acceso"):
            with self.assertRaises(FieldDoesNotExist):
                modelo._meta.get_field(campo)
