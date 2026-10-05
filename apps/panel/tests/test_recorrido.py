"""Recorrido del administrador por el panel integrado, de punta a punta."""

import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.productos.models import Producto
from apps.proyectos.models import Proyecto
from apps.servicios.models import TipoServicio
from apps.sitios.models import Sitio
from apps.visitas.models import Foto, Visita

MEDIA_RECORRIDO = tempfile.mkdtemp(prefix="macontrol-recorrido-test-")


def _jpeg():
    salida = BytesIO()
    Image.new("RGB", (40, 30), "blue").save(salida, format="JPEG")
    return salida.getvalue()


@override_settings(MEDIA_ROOT=MEDIA_RECORRIDO)
class RecorridoTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_RECORRIDO, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            "adm-rec", password="x", rol=User.Rol.ADMINISTRADOR
        )
        cls.empleado = User.objects.create_user(
            "emp-rec", password="x", rol=User.Rol.EMPLEADO
        )
        cliente = Cliente.objects.create(razon_social="Cliente Recorrido")
        cls.sitio = Sitio.objects.create(
            cliente=cliente,
            nombre="Depósito central",
            latitud=Decimal("-34.603700"),
            longitud=Decimal("-58.381600"),
        )
        tipo = TipoServicio.objects.create(nombre="Desinsectación", slug="des-rec")
        cls.proyecto = Proyecto.objects.create(
            sitio=cls.sitio,
            tipo_servicio=tipo,
            titulo="Desinsectación mensual",
            encargado_inicial=cls.empleado,
            encargado_actual=cls.empleado,
        )
        cls.producto = Producto.objects.create(nombre_comercial="Gel cucarachicida")

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.client.force_login(self.admin)

    def _get_200(self, url):
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200, url)
        return respuesta

    def test_administrador_recorre_el_panel(self):
        # Tablero y mapa.
        self._get_200(reverse("panel:inicio"))
        self._get_200(reverse("panel:mapa"))
        datos = self._get_200(reverse("panel:mapa_datos")).json()
        url_sitio = reverse("panel:sitios:ficha", args=[self.sitio.pk])
        sitio = next(s for s in datos["sitios"] if s["id"] == self.sitio.pk)
        self.assertEqual(sitio["url_ficha"], url_sitio)

        # Ficha de sitio y ficha de proyecto, que ofrece asignar y cargar a mano.
        self._get_200(url_sitio)
        url_proyecto = reverse("panel:proyectos:ficha", args=[self.proyecto.pk])
        url_asignar = reverse("panel:visitas:asignar", args=[self.proyecto.pk])
        url_manual = reverse("panel:visitas:manual", args=[self.proyecto.pk])
        ficha_proyecto = self._get_200(url_proyecto)
        self.assertContains(ficha_proyecto, url_asignar)
        self.assertContains(ficha_proyecto, url_manual)

        # Asignar una visita pendiente al empleado.
        self._get_200(url_asignar)
        respuesta = self.client.post(
            url_asignar,
            {
                "empleado": self.empleado.pk,
                "programada_para": timezone.localdate() + timedelta(days=1),
            },
        )
        self.assertRedirects(respuesta, url_proyecto)
        pendiente = Visita.objects.get(
            proyecto=self.proyecto, estado=Visita.Estado.PENDIENTE
        )

        # Completar esa pendiente con la carga manual.
        self._get_200(url_manual)
        respuesta = self.client.post(
            url_manual,
            {
                "empleado": self.empleado.pk,
                "puntos": [self.sitio.puntos.get(orden=0).pk],
                "pendiente": pendiente.pk,
                "motivo": "El empleado no tenía conexión",
                "realizada_en": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
                "productos-TOTAL_FORMS": 1,
                "productos-INITIAL_FORMS": 0,
                "productos-MIN_NUM_FORMS": 0,
                "productos-MAX_NUM_FORMS": 30,
                "productos-0-producto": self.producto.pk,
                "productos-0-lote": "L7",
                "productos-0-dosis": "1.5",
                "productos-0-unidad": "g",
                "fotos": [
                    SimpleUploadedFile("f.jpg", _jpeg(), content_type="image/jpeg")
                ],
            },
        )
        url_visita = reverse("panel:visitas:ficha", args=[pendiente.pk])
        self.assertRedirects(respuesta, url_visita)

        # La visita final quedó realizada y su ficha y su foto se ven.
        pendiente.refresh_from_db()
        self.assertEqual(pendiente.estado, Visita.Estado.REALIZADA)
        self.assertEqual(pendiente.origen, Visita.Origen.MANUAL)
        self.assertEqual(pendiente.asignada_por, self.admin)
        self._get_200(url_visita)
        foto = Foto.objects.get(revision__visita=pendiente)
        self._get_200(reverse("panel:visitas:foto", args=[foto.codigo]))
        self._get_200(url_proyecto)
