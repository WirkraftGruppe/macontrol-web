from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.visitas.models import Visita
from apps.visitas.tests.test_models import crear_revision, crear_visita


def abierta_hace(horas, **extra):
    return crear_visita(
        origen=Visita.Origen.APP,
        estado=Visita.Estado.ABIERTA,
        abierta_en=timezone.now() - timedelta(hours=horas),
        **extra,
    )


class CerrarAbiertasTests(TestCase):
    def ejecutar(self):
        salida = StringIO()
        call_command("cerrar_visitas_abiertas", stdout=salida)
        return salida.getvalue()

    def test_cierra_por_sistema_pasado_el_maximo(self):
        vieja = abierta_hace(20)
        crear_revision(vieja, realizada_en=timezone.now() - timedelta(hours=19))
        ultima = crear_revision(
            vieja, realizada_en=timezone.now() - timedelta(hours=18)
        )
        reciente = abierta_hace(2)
        crear_revision(reciente)
        salida = self.ejecutar()
        vieja.refresh_from_db()
        reciente.refresh_from_db()
        self.assertEqual(vieja.estado, Visita.Estado.REALIZADA)
        self.assertEqual(vieja.cierre, Visita.Cierre.SISTEMA)
        # La hora de cierre es la de la última revisión, no la del comando.
        self.assertEqual(vieja.cerrada_en, ultima.realizada_en)
        self.assertEqual(reciente.estado, Visita.Estado.ABIERTA)
        proyecto = vieja.proyecto
        proyecto.refresh_from_db()
        self.assertEqual(proyecto.encargado_actual, vieja.empleado)
        self.assertIn("1", salida)

    @override_settings(VISITA_ABIERTA_MAXIMO_HORAS=1)
    def test_el_maximo_sale_del_setting(self):
        visita = abierta_hace(2)
        crear_revision(visita)
        self.ejecutar()
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.REALIZADA)

    def test_sin_revisiones_vuelve_a_pendiente_o_se_cancela(self):
        asignador = User.objects.create_user(
            username="adm-cmd", password="x", rol=User.Rol.ADMINISTRADOR
        )
        asignada = abierta_hace(20, asignada_por=asignador)
        propia = abierta_hace(20)
        self.ejecutar()
        asignada.refresh_from_db()
        propia.refresh_from_db()
        self.assertEqual(asignada.estado, Visita.Estado.PENDIENTE)
        self.assertIsNone(asignada.abierta_en)
        self.assertEqual(propia.estado, Visita.Estado.CANCELADA)
        self.assertIsNone(propia.cerrada_en)
        for visita in (asignada, propia):
            proyecto = visita.proyecto
            proyecto.refresh_from_db()
            self.assertIsNone(proyecto.proxima_visita)
