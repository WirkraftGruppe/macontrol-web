"""Panel de Visitas: listado, ficha, foto, revisión de incidencia y asignación."""

import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from uuid import uuid4

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.proyectos.models import Proyecto
from apps.visitas.models import Foto, Visita

from .test_models import crear_visita

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="macontrol-panel-test-")


def _jpeg():
    salida = BytesIO()
    Image.new("RGB", (40, 30), "red").save(salida, format="JPEG")
    return salida.getvalue()


class BaseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.visita = crear_visita(
            estado=Visita.Estado.REALIZADA,
            realizada_en=timezone.now(),
            origen=Visita.Origen.MANUAL,
            motivo_manual="Carga",
        )
        cls.proyecto = cls.visita.proyecto
        cls.empleado = cls.visita.empleado
        cls.admin = User.objects.create_user(
            "adm-pv", password="x", rol=User.Rol.ADMINISTRADOR
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def otra_visita(self, **extra):
        datos = {
            "proyecto": self.proyecto,
            "empleado": self.empleado,
            "origen": Visita.Origen.MANUAL,
            "motivo_manual": "Carga",
            "estado": Visita.Estado.REALIZADA,
            "realizada_en": timezone.now(),
        }
        datos.update(extra)
        return Visita.objects.create(**datos)


class ListadoVisitasTests(BaseTests):
    def _pks(self, **parametros):
        respuesta = self.client.get(reverse("panel:visitas:listado"), parametros)
        self.assertEqual(respuesta.status_code, 200)
        return {v.pk for v in respuesta.context["visitas"]}

    def test_filtra_incidencias_sin_revisar(self):
        sin_revisar = self.otra_visita(incidencia=True, incidencia_detalle="Rotura")
        revisada = self.otra_visita(
            incidencia=True,
            incidencia_revisada_por=self.admin,
            incidencia_revisada_en=timezone.now(),
        )
        self.assertEqual(self._pks(incidencia="sin_revisar"), {sin_revisar.pk})
        self.assertEqual(self._pks(incidencia="todas"), {sin_revisar.pk, revisada.pk})
        self.assertIn(self.visita.pk, self._pks())

    def test_filtra_por_empleado_proyecto_y_estado(self):
        pendiente = self.otra_visita(
            estado=Visita.Estado.PENDIENTE, realizada_en=None, motivo_manual=""
        )
        self.assertEqual(self._pks(estado="pendiente"), {pendiente.pk})
        self.assertEqual(
            self._pks(empleado=self.empleado.pk, proyecto=self.proyecto.pk),
            {self.visita.pk, pendiente.pk},
        )
        self.assertEqual(self._pks(empleado=self.admin.pk), set())

    def test_parcial_htmx_lleva_id_listado(self):
        respuesta = self.client.get(
            reverse("panel:visitas:listado"), headers={"HX-Request": "true"}
        )
        self.assertContains(respuesta, 'id="listado"')
        self.assertNotContains(respuesta, "<html")


class RevisarIncidenciaTests(BaseTests):
    def test_marca_revisada_por_el_administrador(self):
        visita = self.otra_visita(incidencia=True)
        url = reverse("panel:visitas:revisar_incidencia", args=[visita.pk])
        respuesta = self.client.post(url)
        self.assertRedirects(
            respuesta, reverse("panel:visitas:ficha", args=[visita.pk])
        )
        visita.refresh_from_db()
        self.assertEqual(visita.incidencia_revisada_por, self.admin)
        self.assertIsNotNone(visita.incidencia_revisada_en)

    def test_empleado_no_puede_revisar(self):
        visita = self.otra_visita(incidencia=True)
        self.client.force_login(self.empleado)
        url = reverse("panel:visitas:revisar_incidencia", args=[visita.pk])
        self.assertEqual(self.client.post(url).status_code, 403)
        visita.refresh_from_db()
        self.assertIsNone(visita.incidencia_revisada_en)

    def test_sin_incidencia_no_se_marca(self):
        url = reverse("panel:visitas:revisar_incidencia", args=[self.visita.pk])
        self.client.post(url)
        self.visita.refresh_from_db()
        self.assertIsNone(self.visita.incidencia_revisada_en)

    def test_get_no_esta_permitido(self):
        url = reverse("panel:visitas:revisar_incidencia", args=[self.visita.pk])
        self.assertEqual(self.client.get(url).status_code, 405)


class FichaVisitaTests(BaseTests):
    def test_historial_no_muestra_coordenadas(self):
        self.visita.latitud = Decimal("-35.123456")
        self.visita.longitud = Decimal("-57.654321")
        self.visita.precision_m = Decimal("12.5")
        self.visita.datos = {"secreto": "valor-reservado"}
        self.visita.observaciones = "Cambio visible"
        self.visita.save()
        respuesta = self.client.get(
            reverse("panel:visitas:ficha", args=[self.visita.pk])
        )
        self.assertEqual(respuesta.status_code, 200)
        contenido = respuesta.content.decode()
        self.assertIn("Historial", contenido)
        self.assertIn("observaciones", contenido)
        for prohibido in ("-35.123456", "-57.654321", "12.5", "valor-reservado"):
            self.assertNotIn(prohibido, contenido)
        for campo in ("latitud", "longitud", "precisión"):
            self.assertNotIn(campo, contenido.lower())

    def test_muestra_planilla_del_esquema_copiado(self):
        self.visita.esquema_planilla = [
            {"clave": "cebos", "etiqueta": "Cantidad de cebos", "tipo": "numero"}
        ]
        self.visita.datos = {"cebos": 7}
        self.visita.save()
        respuesta = self.client.get(
            reverse("panel:visitas:ficha", args=[self.visita.pk])
        )
        self.assertContains(respuesta, "Cantidad de cebos")

    def test_ficha_inexistente_da_404(self):
        respuesta = self.client.get(reverse("panel:visitas:ficha", args=[999999]))
        self.assertEqual(respuesta.status_code, 404)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class FotoPanelTests(BaseTests):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def _foto(self):
        return Foto.objects.create(
            visita=self.visita,
            imagen=SimpleUploadedFile("x.jpg", _jpeg(), content_type="image/jpeg"),
        )

    def test_administrador_recibe_la_imagen_con_cabeceras(self):
        foto = self._foto()
        respuesta = self.client.get(reverse("panel:visitas:foto", args=[foto.codigo]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Content-Type"], "image/jpeg")
        self.assertEqual(respuesta["Cache-Control"], "private, no-store")
        self.assertEqual(respuesta["X-Content-Type-Options"], "nosniff")
        self.assertTrue(b"".join(respuesta.streaming_content).startswith(b"\xff\xd8"))

    def test_foto_exige_administrador(self):
        foto = self._foto()
        url = reverse("panel:visitas:foto", args=[foto.codigo])
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.logout()
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/panel/ingresar/", respuesta["Location"])

    def test_foto_sin_archivo_da_404(self):
        foto = self._foto()
        foto.imagen.storage.delete(foto.imagen.name)
        url = reverse("panel:visitas:foto", args=[foto.codigo])
        self.assertEqual(self.client.get(url).status_code, 404)
        inexistente = reverse("panel:visitas:foto", args=[uuid4()])
        self.assertEqual(self.client.get(inexistente).status_code, 404)


class AsignarTests(BaseTests):
    def _url(self, proyecto_pk=None):
        return reverse("panel:visitas:asignar", args=[proyecto_pk or self.proyecto.pk])

    def test_crea_pendiente_para_empleado(self):
        fecha = timezone.localdate() + timedelta(days=3)
        respuesta = self.client.post(
            self._url(), {"empleado": self.empleado.pk, "programada_para": fecha}
        )
        self.assertRedirects(
            respuesta, reverse("panel:proyectos:ficha", args=[self.proyecto.pk])
        )
        visita = Visita.objects.get(estado=Visita.Estado.PENDIENTE)
        self.assertEqual(visita.proyecto, self.proyecto)
        self.assertEqual(visita.empleado, self.empleado)
        self.assertEqual(visita.programada_para, fecha)
        self.assertEqual(visita.asignada_por, self.admin)

    def test_rechaza_administrador_inactivo_y_fecha_pasada(self):
        ayer = timezone.localdate() - timedelta(days=1)
        manana = timezone.localdate() + timedelta(days=1)
        inactivo = User.objects.create_user(
            "emp-off", password="x", rol=User.Rol.EMPLEADO, is_active=False
        )
        for datos in (
            {"empleado": self.admin.pk, "programada_para": manana},
            {"empleado": inactivo.pk, "programada_para": manana},
            {"empleado": self.empleado.pk, "programada_para": ayer},
        ):
            respuesta = self.client.post(self._url(), datos)
            self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Visita.objects.filter(estado=Visita.Estado.PENDIENTE))

    def test_rechaza_proyecto_no_activo(self):
        otro = Proyecto.objects.exclude(estado=Proyecto.Estado.ACTIVO).count()
        self.assertEqual(otro, 0)
        estados = [e for e in Proyecto.Estado.values if e != Proyecto.Estado.ACTIVO]
        self.proyecto.estado = estados[0]
        self.proyecto.save()
        manana = timezone.localdate() + timedelta(days=1)
        respuesta = self.client.post(
            self._url(), {"empleado": self.empleado.pk, "programada_para": manana}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Visita.objects.filter(estado=Visita.Estado.PENDIENTE))

    def test_proyecto_inexistente_da_404(self):
        self.assertEqual(self.client.get(self._url(999999)).status_code, 404)
