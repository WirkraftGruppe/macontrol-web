import shutil
import tempfile
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image

from apps.servicios.models import CampoPlanilla
from apps.visitas.models import Foto, Visita
from apps.visitas.services import registrar_visita_realizada
from apps.visitas.tests.test_models import crear_visita

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="visitas-test-")
COORDENADAS = {"latitud": Decimal("-35.1"), "longitud": Decimal("-57.7")}


def jpeg_chico():
    buffer = BytesIO()
    Image.new("RGB", (20, 20), "red").save(buffer, "JPEG")
    return SimpleUploadedFile("f.jpg", buffer.getvalue(), content_type="image/jpeg")


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class RegistrarVisitaTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def setUp(self):
        self.ahora = timezone.make_aware(datetime(2026, 10, 3, 12, 0))

    def con_foto(self, visita):
        Foto.objects.create(visita=visita, imagen=jpeg_chico())

    def test_actualiza_encargado_actual_y_proxima_visita(self):
        visita = crear_visita(**COORDENADAS)
        self.con_foto(visita)
        proyecto = visita.proyecto
        proyecto.frecuencia_dias = 30
        proyecto.save()
        resultado = registrar_visita_realizada(visita, visita.empleado, self.ahora)
        self.assertEqual(resultado.estado, Visita.Estado.REALIZADA)
        self.assertEqual(resultado.realizada_en, self.ahora)
        proyecto.refresh_from_db()
        self.assertEqual(proyecto.encargado_actual, visita.empleado)
        self.assertEqual(
            proyecto.proxima_visita,
            timezone.localdate(self.ahora) + timedelta(days=30),
        )

    def test_sin_frecuencia_no_toca_proxima_visita(self):
        visita = crear_visita(origen=Visita.Origen.MANUAL, motivo_manual="Carga")
        proyecto = visita.proyecto
        proyecto.proxima_visita = date(2027, 1, 1)
        proyecto.save()
        registrar_visita_realizada(visita, visita.empleado, self.ahora)
        proyecto.refresh_from_db()
        self.assertEqual(proyecto.proxima_visita, date(2027, 1, 1))

    def test_origen_app_exige_coordenadas_y_foto(self):
        visita = crear_visita()
        proyecto = visita.proyecto
        antes = (proyecto.encargado_actual_id, proyecto.proxima_visita)

        def verificar_rechazo(nombre):
            with self.subTest(nombre):
                with self.assertRaises(ValidationError):
                    registrar_visita_realizada(visita, visita.empleado, self.ahora)
                visita.refresh_from_db()
                self.assertEqual(visita.estado, Visita.Estado.PENDIENTE)
                self.assertIsNone(visita.realizada_en)
                proyecto.refresh_from_db()
                self.assertEqual(
                    (proyecto.encargado_actual_id, proyecto.proxima_visita), antes
                )

        verificar_rechazo("sin coordenadas ni foto")
        visita.latitud, visita.longitud = COORDENADAS.values()
        visita.save()
        verificar_rechazo("sin foto")
        visita.latitud = visita.longitud = None
        visita.save()
        self.con_foto(visita)
        verificar_rechazo("sin coordenadas")

    def test_origen_app_con_coordenadas_y_foto_se_registra(self):
        visita = crear_visita(**COORDENADAS)
        self.con_foto(visita)
        registrar_visita_realizada(visita, visita.empleado, self.ahora)
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.REALIZADA)

    def test_origen_manual_exige_motivo(self):
        visita = crear_visita(origen=Visita.Origen.MANUAL, motivo_manual="   ")
        with self.assertRaises(ValidationError):
            registrar_visita_realizada(visita, visita.empleado, self.ahora)
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.PENDIENTE)
        visita.motivo_manual = "Sin señal en el sitio"
        visita.save()
        registrar_visita_realizada(visita, visita.empleado, self.ahora)
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.REALIZADA)

    def test_guarda_copia_del_esquema_de_planilla(self):
        visita = crear_visita(origen=Visita.Origen.MANUAL, motivo_manual="Carga")
        campo = CampoPlanilla.objects.create(
            tipo_servicio=visita.proyecto.tipo_servicio,
            orden=1,
            etiqueta="Cebos",
            clave="cebos",
            tipo=CampoPlanilla.Tipo.NUMERO,
        )
        registrar_visita_realizada(visita, visita.empleado, self.ahora)
        visita.refresh_from_db()
        self.assertEqual(len(visita.esquema_planilla), 1)
        self.assertEqual(visita.esquema_planilla[0]["clave"], "cebos")
        campo.etiqueta = "Otra"
        campo.save()
        visita.refresh_from_db()
        self.assertEqual(visita.esquema_planilla[0]["etiqueta"], "Cebos")

    def test_rechaza_visita_no_pendiente(self):
        visita = crear_visita(
            origen=Visita.Origen.MANUAL,
            motivo_manual="Carga",
            estado=Visita.Estado.CANCELADA,
        )
        with self.assertRaises(ValidationError):
            registrar_visita_realizada(visita, visita.empleado, self.ahora)
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.CANCELADA)
