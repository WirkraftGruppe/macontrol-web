"""Pruebas de ``cargar_demo``: datos genéricos, idempotente y solo con SQLite."""

import os
import shutil
import tempfile
from datetime import timedelta
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.panel.demo import _es_sqlite
from apps.sitios.models import Plano, PuntoControl, Sitio
from apps.visitas.models import Foto, Revision, Visita

MEDIA_DEMO = tempfile.mkdtemp(prefix="macontrol-demo-test-")


@override_settings(MEDIA_ROOT=MEDIA_DEMO)
class CargarDemoTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_DEMO, ignore_errors=True)

    def _cargar(self):
        call_command("cargar_demo", stdout=StringIO())

    def _conteos(self):
        return {
            modelo.__name__: modelo.objects.count()
            for modelo in (User, Cliente, Sitio, PuntoControl, Plano, Visita, Revision)
        } | {"Foto": Foto.objects.count()}

    @override_settings(DEBUG=True)
    def test_crea_puntos_plano_y_revisiones_idempotente(self):
        self._cargar()
        primera = self._conteos()

        # Todo es genérico: ningún nombre de cliente sale de la empresa real.
        for cliente in Cliente.objects.all():
            self.assertRegex(cliente.razon_social, r"^Cliente Demo \d+$")
            self.assertEqual(cliente.cuit, "")

        # Un plano por cada sitio de más de tres puntos, con marcadores en 0..1.
        for sitio in Sitio.objects.all():
            puntos = list(sitio.puntos.all())
            self.assertEqual(sitio.planos.count(), 1 if len(puntos) > 3 else 0)
            for punto in puntos:
                if sitio.planos.exists():
                    self.assertTrue(0 <= punto.x <= 1 and 0 <= punto.y <= 1)
                self.assertIsNotNone(punto.latitud)
        self.assertEqual(Plano.objects.count(), 1)
        plano = Plano.objects.get()
        self.assertGreater(plano.ancho_px, 0)

        # Visitas realizadas con revisiones y fotos, y una abierta.
        self.assertGreaterEqual(
            Visita.objects.filter(estado=Visita.Estado.REALIZADA).count(), 2
        )
        self.assertEqual(Visita.objects.filter(estado=Visita.Estado.ABIERTA).count(), 1)
        self.assertGreaterEqual(primera["Revision"], 4)
        self.assertGreaterEqual(primera["Foto"], primera["Revision"])
        self.assertEqual(User.objects.filter(rol=User.Rol.ADMINISTRADOR).count(), 1)
        self.assertEqual(User.objects.filter(rol=User.Rol.EMPLEADO).count(), 1)

        # Segunda corrida: no duplica nada.
        self._cargar()
        self.assertEqual(self._conteos(), primera)

    @override_settings(DEBUG=True)
    def test_falla_tardia_no_deja_planos_huerfanos(self):
        with (
            tempfile.TemporaryDirectory() as media,
            override_settings(MEDIA_ROOT=media),
        ):
            ruta = "apps.panel.management.commands.cargar_demo.Command._proyecto"
            with mock.patch(ruta, side_effect=RuntimeError("falla tardía")):
                with self.assertRaisesMessage(RuntimeError, "falla tardía"):
                    self._cargar()
            self.assertEqual(Plano.objects.count(), 0)
            archivos = [f for _, _, fs in os.walk(media) for f in fs]
            self.assertEqual(archivos, [])

    @override_settings(DEBUG=True, ATRASO_MAXIMO_HORAS=48)
    def test_atraso_acotado_al_maximo(self):
        antes = timezone.now()
        self._cargar()
        limite = antes - timedelta(hours=48)
        self.assertEqual(
            Visita.objects.filter(estado=Visita.Estado.REALIZADA).count(), 3
        )
        self.assertFalse(Revision.objects.filter(realizada_en__lt=limite).exists())

    @override_settings(DEBUG=True)
    def test_corrida_incompleta_se_completa_en_la_siguiente(self):
        self._cargar()
        # Una corrida fallida dejó la primera jornada abierta, sin cerrar.
        primera = Visita.objects.filter(estado=Visita.Estado.REALIZADA).first()
        Visita.objects.filter(proyecto=primera.proyecto).update(
            estado=Visita.Estado.ABIERTA
        )
        self._cargar()
        self.assertEqual(
            Visita.objects.filter(estado=Visita.Estado.REALIZADA).count(), 3
        )

    @override_settings(DEBUG=False)
    def test_rechaza_sin_debug_y_no_toca_la_base(self):
        with self.assertRaisesMessage(CommandError, "DEBUG activo"):
            self._cargar()
        self.assertEqual(Cliente.objects.count(), 0)
        self.assertFalse(User.objects.exists())

    @override_settings(DEBUG=True)
    def test_rechaza_entorno_que_no_es_development(self):
        with mock.patch.dict(os.environ, {"DJANGO_ENV": "production"}):
            with self.assertRaisesMessage(CommandError, "DJANGO_ENV=development"):
                self._cargar()
        self.assertEqual(Cliente.objects.count(), 0)
        self.assertFalse(User.objects.exists())

    def test_base_local_rechaza_host_remoto(self):
        postgres = "django.db.backends.postgresql"
        self.assertTrue(_es_sqlite({"ENGINE": "django.db.backends.sqlite3"}))
        self.assertFalse(_es_sqlite({"ENGINE": postgres, "HOST": "db.remoto.com"}))
        self.assertFalse(_es_sqlite({"ENGINE": postgres, "HOST": "localhost"}))
        self.assertFalse(
            _es_sqlite({"ENGINE": postgres, "HOST": "", "OPTIONS": {"host": "remoto"}})
        )
        self._rechaza_con({"ENGINE": postgres, "HOST": "db.remoto.com"})

    def test_rechaza_postgres_local(self):
        postgres = "django.db.backends.postgresql"
        self._rechaza_con({"ENGINE": postgres, "HOST": "localhost"})

    def _rechaza_con(self, configuracion):
        """El comando rechaza esa base con el mensaje de SQLite y sin escribir."""
        falsa = mock.Mock(settings_dict=configuracion)
        ruta = "apps.panel.demo.connection"
        with override_settings(DEBUG=True), mock.patch(ruta, falsa):
            with self.assertRaisesMessage(CommandError, "solo corre contra SQLite"):
                self._cargar()
        self.assertEqual(Cliente.objects.count(), 0)
        self.assertFalse(User.objects.exists())

    @override_settings(DEBUG=True)
    def test_avisa_usuario_demo_existente_sin_modificarlo(self):
        previo = User.objects.create_user(
            "demo-admin", password="otra-clave", rol=User.Rol.EMPLEADO
        )
        salida, errores = StringIO(), StringIO()
        call_command("cargar_demo", stdout=salida, stderr=errores)
        previo.refresh_from_db()
        self.assertEqual(previo.rol, User.Rol.EMPLEADO)
        self.assertTrue(previo.check_password("otra-clave"))
        self.assertIn("demo-admin", errores.getvalue())
        self.assertNotIn("demo-admin", salida.getvalue())
        self.assertIn("demo-empleado", salida.getvalue())
