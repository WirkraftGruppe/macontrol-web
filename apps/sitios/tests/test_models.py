import datetime
import io
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection, transaction
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from PIL import Image

from apps.clientes.models import Cliente
from apps.proyectos.models import UMBRAL_PROXIMA_DIAS, Proyecto
from apps.servicios.models import TipoServicio
from apps.sitios import services
from apps.sitios.estado import (
    GRAVEDAD_PUNTO,
    EstadoPunto,
    estado_revision,
    estados_de_puntos,
    peor_estado_punto,
)
from apps.sitios.models import Plano, PuntoControl, Sitio
from apps.visitas.models import Revision, Visita


class SitioTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(razon_social="ACME")

    def _sitio(self, nombre, **extra):
        return Sitio.objects.create(cliente=self.cliente, nombre=nombre, **extra)

    def test_sitio_ya_no_tiene_qr_propio(self):
        for campo in ("qr_codigo", "qr_impreso_el"):
            for modelo in (Sitio, Sitio.history.model):
                with self.assertRaises(FieldDoesNotExist):
                    modelo._meta.get_field(campo)

    def test_historial_registra_cambios(self):
        sitio = self._sitio("Planta 1")
        sitio.nombre = "Planta Norte"
        sitio.save()
        self.assertEqual(sitio.history.count(), 2)

    def test_historial_no_guarda_contacto_ni_telefono(self):
        modelo = Sitio.history.model
        for campo in ("contacto_en_sitio", "telefono_en_sitio"):
            with self.assertRaises(FieldDoesNotExist):
                modelo._meta.get_field(campo)


class PuntoControlTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(razon_social="ACME")
        self.sitio = Sitio.objects.create(cliente=self.cliente, nombre="Planta 1")

    def test_qr_unico_y_sitio_inactivo_desactiva_puntos(self):
        uno = PuntoControl.objects.create(sitio=self.sitio, nombre="Depósito", orden=1)
        dos = PuntoControl.objects.create(sitio=self.sitio, nombre="Cocina", orden=2)
        self.assertNotEqual(uno.qr_codigo, dos.qr_codigo)
        self.assertIs(PuntoControl._meta.get_field("qr_codigo").editable, False)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PuntoControl.objects.create(
                    sitio=self.sitio, nombre="Copia", qr_codigo=uno.qr_codigo
                )
        self.sitio.activo = False
        self.sitio.save()
        self.assertFalse(self.sitio.puntos.filter(activo=True).exists())
        self.assertEqual(self.sitio.puntos.count(), 3)

    def test_sitio_nuevo_recibe_punto_general_con_qr_propio(self):
        general = self.sitio.puntos.get()
        self.assertEqual(general.nombre, "General")
        self.assertEqual(general.orden, 0)
        otro = Sitio.objects.create(cliente=self.cliente, nombre="Planta 2")
        self.assertNotEqual(general.qr_codigo, otro.puntos.get().qr_codigo)
        self.sitio.nombre = "Planta Norte"
        self.sitio.save()
        self.assertEqual(self.sitio.puntos.count(), 1)

    def test_reemplazar_foto_borra_la_anterior(self):
        media = tempfile.mkdtemp(prefix="sitios-modelo-test-")
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)
        buffer = io.BytesIO()
        Image.new("RGB", (30, 30), "red").save(buffer, "PNG")
        with override_settings(MEDIA_ROOT=media):
            punto = self.sitio.puntos.get()
            punto.foto = SimpleUploadedFile("a.png", buffer.getvalue())
            punto.save()
            almacenamiento, anterior = punto.foto.storage, punto.foto.name
            punto.foto = SimpleUploadedFile("b.png", buffer.getvalue())
            with self.captureOnCommitCallbacks(execute=True):
                punto.save()
            self.assertNotEqual(punto.foto.name, anterior)
            self.assertFalse(almacenamiento.exists(anterior))
            self.assertTrue(almacenamiento.exists(punto.foto.name))
            nombre = punto.foto.name
            with self.captureOnCommitCallbacks(execute=True):
                punto.nombre = "Entrada"
                punto.save()
            self.assertTrue(almacenamiento.exists(nombre))

    def test_no_desactiva_el_ultimo_punto_y_reactivar_sitio_reactiva(self):
        general = self.sitio.puntos.get()
        with self.assertRaises(ValidationError):
            services.desactivar_punto(general)
        general.refresh_from_db()
        self.assertTrue(general.activo)
        cocina = PuntoControl.objects.create(sitio=self.sitio, nombre="Cocina", orden=1)
        deposito = PuntoControl.objects.create(
            sitio=self.sitio, nombre="Depósito", orden=2
        )
        services.desactivar_punto(deposito)
        self.sitio.activo = False
        self.sitio.save()
        self.assertFalse(self.sitio.puntos.filter(activo=True).exists())
        self.sitio.activo = True
        self.sitio.save()
        general.refresh_from_db()
        cocina.refresh_from_db()
        deposito.refresh_from_db()
        self.assertTrue(general.activo)
        self.assertTrue(cocina.activo)
        self.assertFalse(deposito.activo, "Lo apagó una persona, no el sitio")
        self.assertEqual(
            cocina.history.first().history_change_reason, "Sitio reactivado"
        )
        self.assertEqual(
            deposito.history.first().history_change_reason, "Punto desactivado"
        )

    def test_clean_rechaza_activo_en_sitio_inactivo_y_plano_ajeno(self):
        otro = Sitio.objects.create(cliente=self.cliente, nombre="Planta 2")
        plano = Plano(sitio=otro, nombre="Planta baja")
        plano.ancho_px = plano.alto_px = 10
        Plano.objects.bulk_create([plano])
        punto = PuntoControl(sitio=self.sitio, nombre="Techo", plano=plano)
        with self.assertRaises(ValidationError) as error:
            punto.clean()
        self.assertIn("plano", error.exception.message_dict)
        Sitio.objects.filter(pk=self.sitio.pk).update(activo=False)
        self.sitio.refresh_from_db()
        punto = PuntoControl(sitio=self.sitio, nombre="Techo", activo=True)
        with self.assertRaises(ValidationError) as error:
            punto.clean()
        self.assertIn("activo", error.exception.message_dict)


class EstadoRevisionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        cliente = Cliente.objects.create(razon_social="ACME")
        self.sitio = Sitio.objects.create(cliente=cliente, nombre="Planta 1")
        self.punto = self.sitio.puntos.get()
        self.empleado = User.objects.create_user(
            "emp", password="x", rol=User.Rol.EMPLEADO
        )
        self.tipo = TipoServicio.objects.create(nombre="Desratización", slug="desrat")
        self.proyecto = self._proyecto("Control", frecuencia_dias=30)

    def _proyecto(self, titulo, **extra):
        return Proyecto.objects.create(
            sitio=self.sitio,
            tipo_servicio=self.tipo,
            titulo=titulo,
            encargado_inicial=self.empleado,
            encargado_actual=self.empleado,
            **extra,
        )

    def _revision(
        self, proyecto, dias_atras, punto=None, estado=Visita.Estado.REALIZADA
    ):
        momento = timezone.now() - datetime.timedelta(days=dias_atras)
        visita = Visita.objects.create(
            proyecto=proyecto,
            empleado=self.empleado,
            origen=Visita.Origen.APP,
            estado=estado,
            abierta_en=momento,
        )
        return Revision.objects.create(
            visita=visita,
            punto=punto or self.punto,
            realizada_en=momento,
            recibida_en=momento,
        )

    def test_vencida_proxima_al_dia_sin_revisar(self):
        self.assertEqual(
            estado_revision(self.punto, self.proyecto), EstadoPunto.SIN_REVISAR
        )
        casos = [
            (35, EstadoPunto.VENCIDA),
            (30 - 3, EstadoPunto.PROXIMA),
            (30 - UMBRAL_PROXIMA_DIAS, EstadoPunto.PROXIMA),
            (10, EstadoPunto.AL_DIA),
        ]
        for dias, esperado in casos:
            with self.subTest(dias=dias):
                Revision.objects.all().delete()
                self._revision(self.proyecto, dias)
                self.assertEqual(estado_revision(self.punto, self.proyecto), esperado)
        sin_frecuencia = self._proyecto("Sin frecuencia")
        self.assertEqual(
            estado_revision(self.punto, sin_frecuencia), EstadoPunto.SIN_REVISAR
        )
        self._revision(sin_frecuencia, 400)
        self.assertEqual(
            estado_revision(self.punto, sin_frecuencia), EstadoPunto.AL_DIA
        )

    def test_cuentan_abiertas_y_la_ultima_pero_no_canceladas(self):
        self._revision(self.proyecto, 100, estado=Visita.Estado.CANCELADA)
        self.assertEqual(
            estado_revision(self.punto, self.proyecto), EstadoPunto.SIN_REVISAR
        )
        self._revision(self.proyecto, 100)
        self._revision(self.proyecto, 1, estado=Visita.Estado.ABIERTA)
        self._revision(self.proyecto, 0, estado=Visita.Estado.CANCELADA)
        self.assertEqual(estado_revision(self.punto, self.proyecto), EstadoPunto.AL_DIA)
        self.assertEqual(
            estados_de_puntos([self.punto]), {self.punto.pk: EstadoPunto.AL_DIA}
        )

    def _revision_de_administrador(self, dias_atras):
        """Revisión de una visita manual que no cuenta como servicio."""
        revision = self._revision(self.proyecto, dias_atras)
        Visita.objects.filter(pk=revision.visita_id).update(cuenta_como_servicio=False)

    def test_estado_revision_ignora_visitas_de_administrador(self):
        self._revision(self.proyecto, 40)
        self._revision_de_administrador(1)
        self.assertEqual(
            estado_revision(self.punto, self.proyecto), EstadoPunto.VENCIDA
        )

    def test_estados_de_puntos_ignora_visitas_de_administrador(self):
        self._revision(self.proyecto, 40)
        self._revision_de_administrador(1)
        self.assertEqual(
            estados_de_puntos([self.punto]), {self.punto.pk: EstadoPunto.VENCIDA}
        )

    def test_punto_toma_el_peor_estado_de_los_proyectos_activos(self):
        self._revision(self.proyecto, 1)
        self._proyecto("Pausado", estado=Proyecto.Estado.PAUSADO)
        self.assertEqual(
            estados_de_puntos([self.punto])[self.punto.pk], EstadoPunto.AL_DIA
        )
        self._proyecto("Nuevo", frecuencia_dias=10)
        self.assertEqual(
            estados_de_puntos([self.punto])[self.punto.pk], EstadoPunto.SIN_REVISAR
        )

    def test_sitio_sin_proyectos_activos_y_lista_vacia(self):
        self.proyecto.estado = Proyecto.Estado.FINALIZADO
        self.proyecto.save()
        self.assertEqual(
            estados_de_puntos([self.punto]), {self.punto.pk: EstadoPunto.AL_DIA}
        )
        self.assertEqual(estados_de_puntos([]), {})

    def test_peor_estado_y_gravedad(self):
        self.assertEqual(
            sorted(GRAVEDAD_PUNTO, key=GRAVEDAD_PUNTO.get),
            [
                EstadoPunto.AL_DIA,
                EstadoPunto.PROXIMA,
                EstadoPunto.SIN_REVISAR,
                EstadoPunto.VENCIDA,
            ],
        )
        self.assertEqual(
            peor_estado_punto(["al_dia", "sin_revisar", "proxima"]), "sin_revisar"
        )
        self.assertEqual(peor_estado_punto(["proxima", "vencida"]), "vencida")
        self.assertEqual(peor_estado_punto([]), EstadoPunto.AL_DIA)

    def test_estados_de_puntos_consultas_constantes(self):
        def medir(cantidad):
            for i in range(cantidad):
                punto = PuntoControl.objects.create(
                    sitio=self.sitio,
                    nombre=f"P{self.sitio.puntos.count()}",
                    orden=i + 1,
                )
                self._revision(self.proyecto, 5, punto=punto)
            puntos = list(self.sitio.puntos.all())
            with CaptureQueriesContext(connection) as consultas:
                estados = estados_de_puntos(puntos)
            return len(consultas), estados

        pocas, _ = medir(1)
        muchas, estados = medir(6)
        self.assertEqual(pocas, muchas)
        self.assertEqual(len(estados), 8)
