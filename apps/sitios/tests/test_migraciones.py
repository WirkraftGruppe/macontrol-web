import datetime
import uuid
from decimal import Decimal

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

ANTERIOR = [("sitios", "0003_remove_historicalsitio_horario_acceso_and_more")]
PUNTOS = [("sitios", "0004_puntos_control_y_planos")]


def _migrar(destino):
    ejecutor = MigrationExecutor(connection)
    ejecutor.migrate(destino)
    return MigrationExecutor(connection).loader.project_state(destino).apps


class MigracionPuntosTests(TransactionTestCase):
    def tearDown(self):
        ejecutor = MigrationExecutor(connection)
        ejecutor.migrate(ejecutor.loader.graph.leaf_nodes())

    def _sitios_viejos(self):
        apps = _migrar(ANTERIOR)
        Cliente = apps.get_model("clientes", "Cliente")
        Sitio = apps.get_model("sitios", "Sitio")
        cliente = Cliente.objects.create(razon_social="ACME")
        uno = Sitio.objects.create(
            cliente=cliente,
            nombre="Planta 1",
            qr_impreso_el=datetime.date(2026, 1, 5),
        )
        dos = Sitio.objects.create(cliente=cliente, nombre="Planta 2", activo=False)
        return uno, dos

    def test_cada_sitio_recibe_punto_general_con_su_qr(self):
        uno, dos = self._sitios_viejos()
        apps = _migrar(PUNTOS)
        Punto = apps.get_model("sitios", "PuntoControl")
        self.assertEqual(Punto.objects.count(), 2)
        for sitio in (uno, dos):
            punto = Punto.objects.get(sitio_id=sitio.pk)
            self.assertEqual(punto.nombre, "General")
            self.assertEqual(punto.orden, 0)
            self.assertEqual(punto.qr_codigo, sitio.qr_codigo)
            self.assertEqual(punto.qr_impreso_el, sitio.qr_impreso_el)
        self.assertTrue(Punto.objects.get(sitio_id=uno.pk).activo)
        self.assertFalse(Punto.objects.get(sitio_id=dos.pk).activo)

    def test_vuelta_atras_restaura_el_qr_del_sitio_y_reaplica(self):
        uno, _ = self._sitios_viejos()
        apps = _migrar(PUNTOS)
        Punto = apps.get_model("sitios", "PuntoControl")
        nuevo = uuid.uuid4()
        Punto.objects.filter(sitio_id=uno.pk).update(qr_codigo=nuevo)
        apps = _migrar(ANTERIOR)
        Sitio = apps.get_model("sitios", "Sitio")
        self.assertEqual(Sitio.objects.get(pk=uno.pk).qr_codigo, nuevo)
        ejecutor = MigrationExecutor(connection)
        ejecutor.migrate(ejecutor.loader.graph.leaf_nodes())
        apps = (
            MigrationExecutor(connection)
            .loader.project_state(ejecutor.loader.graph.leaf_nodes())
            .apps
        )
        self.assertEqual(apps.get_model("sitios", "PuntoControl").objects.count(), 2)


class QuitarPropuestaTests(TransactionTestCase):
    ANTES = [("sitios", "0006_puntocontrol_foto")]
    DESPUES = [("sitios", "0007_quitar_ubicacion_propuesta")]

    def tearDown(self):
        ejecutor = MigrationExecutor(connection)
        ejecutor.migrate(ejecutor.loader.graph.leaf_nodes())

    def test_propuesta_pendiente_se_aplica_si_no_hay_coordenadas(self):
        apps = _migrar(self.ANTES)
        Cliente = apps.get_model("clientes", "Cliente")
        Sitio = apps.get_model("sitios", "Sitio")
        Punto = apps.get_model("sitios", "PuntoControl")
        sitio = Sitio.objects.create(
            cliente=Cliente.objects.create(razon_social="ACME"), nombre="Planta"
        )
        propuesta = {
            "latitud": "-35.100000",
            "longitud": "-57.500000",
            "precision_m": "8",
        }
        sin_coordenadas = Punto.objects.create(
            sitio=sitio, nombre="A", orden=1, ubicacion_propuesta=propuesta
        )
        con_coordenadas = Punto.objects.create(
            sitio=sitio,
            nombre="B",
            orden=2,
            latitud=Decimal("-36.100000"),
            longitud=Decimal("-58.200000"),
            ubicacion_propuesta=propuesta,
        )
        sin_propuesta = Punto.objects.create(sitio=sitio, nombre="C", orden=3)
        apps = _migrar(self.DESPUES)
        Punto = apps.get_model("sitios", "PuntoControl")
        punto = Punto.objects.get(pk=sin_coordenadas.pk)
        self.assertEqual(punto.latitud, Decimal("-35.1"))
        self.assertEqual(punto.longitud, Decimal("-57.5"))
        punto = Punto.objects.get(pk=con_coordenadas.pk)
        self.assertEqual(punto.latitud, Decimal("-36.1"))
        self.assertEqual(punto.longitud, Decimal("-58.2"))
        punto = Punto.objects.get(pk=sin_propuesta.pk)
        self.assertIsNone(punto.latitud)
