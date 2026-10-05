import datetime
import uuid

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
