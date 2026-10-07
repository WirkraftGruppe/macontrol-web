import datetime
import uuid
from decimal import Decimal

from django.conf import settings
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
    ANTES = [
        ("sitios", "0006_puntocontrol_foto"),
        ("visitas", "0008_ubicacion_y_administrador"),
    ]
    DESPUES = [("sitios", "0007_quitar_ubicacion_propuesta")]

    def tearDown(self):
        ejecutor = MigrationExecutor(connection)
        ejecutor.migrate(ejecutor.loader.graph.leaf_nodes())

    def _escenario(self):
        """Estado previo: un sitio, un empleado y una visita para citar revisiones."""
        apps = _migrar(self.ANTES)
        Cliente = apps.get_model("clientes", "Cliente")
        Sitio = apps.get_model("sitios", "Sitio")
        sitio = Sitio.objects.create(
            cliente=Cliente.objects.create(razon_social="ACME"), nombre="Planta"
        )
        empleado = apps.get_model("accounts", "User").objects.create(
            username="emp", rol="empleado"
        )
        proyecto = apps.get_model("proyectos", "Proyecto").objects.create(
            sitio=sitio,
            tipo_servicio=apps.get_model("servicios", "TipoServicio").objects.create(
                nombre="Control"
            ),
            titulo="Control mensual",
            encargado_inicial=empleado,
            encargado_actual=empleado,
        )
        self.visita = apps.get_model("visitas", "Visita").objects.create(
            proyecto=proyecto, empleado=empleado, origen="manual"
        )
        self.empleado = empleado
        self.apps_antes = apps
        self.sitio = sitio
        return apps

    def _punto(self, orden, propuesta, **extra):
        Punto = self.apps_antes.get_model("sitios", "PuntoControl")
        return Punto.objects.create(
            sitio=self.sitio,
            nombre=f"P{orden}",
            orden=orden,
            ubicacion_propuesta=propuesta,
            **extra,
        )

    def _revision(self, punto=None, **extra):
        """Revisión con las coordenadas y la precisión de ``_propuesta`` por defecto."""
        ahora = datetime.datetime(2026, 1, 5, 10, tzinfo=datetime.UTC)
        Punto = self.apps_antes.get_model("sitios", "PuntoControl")
        datos = {
            "latitud": Decimal("-35.1"),
            "longitud": Decimal("-57.5"),
            "precision_m": 8,
            **extra,
        }
        return self.apps_antes.get_model("visitas", "Revision").objects.create(
            visita=self.visita,
            punto=punto or Punto.objects.first(),
            realizada_en=ahora,
            recibida_en=ahora,
            **datos,
        )

    def _punto_propuesto(self, orden, json=None, revision=None, **extra):
        """Punto con una propuesta respaldada por una revisión de ese mismo punto.

        ``json`` pisa las coordenadas del JSON; ``revision`` pisa las de la revisión."""
        punto = self._punto(orden, None, **extra)
        rev = self._revision(punto=punto, **(revision or {}))
        propuesta = self._propuesta(rev.pk, **(json or {}))
        Punto = self.apps_antes.get_model("sitios", "PuntoControl")
        Punto.objects.filter(pk=punto.pk).update(ubicacion_propuesta=propuesta)
        return punto, rev

    @staticmethod
    def _propuesta(revision, latitud="-35.100000", longitud="-57.500000"):
        return {
            "latitud": latitud,
            "longitud": longitud,
            "precision_m": "8",
            "revision": revision,
        }

    def test_propuesta_pendiente_se_aplica_si_no_hay_coordenadas(self):
        self._escenario()
        self._punto(0, None)
        sin_coordenadas, _ = self._punto_propuesto(1)
        con_coordenadas, _ = self._punto_propuesto(
            2, latitud=Decimal("-36.100000"), longitud=Decimal("-58.200000")
        )
        sin_propuesta = self._punto(3, None)
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

    def test_propuesta_aplicada_deja_historial_con_la_revision(self):
        self._escenario()
        base = self._punto(0, None)
        punto, revision = self._punto_propuesto(1)
        apps = _migrar(self.DESPUES)
        Historico = apps.get_model("sitios", "HistoricalPuntoControl")
        filas = Historico.objects.filter(id=punto.pk)
        self.assertEqual(filas.count(), 1)
        fila = filas.get()
        self.assertEqual(fila.history_type, "~")
        self.assertEqual(fila.history_user_id, self.empleado.pk)
        self.assertIn(f"revisión {revision.pk}", fila.history_change_reason)
        self.assertEqual(fila.latitud, Decimal("-35.1"))
        self.assertEqual(fila.nombre, "P1")
        self.assertFalse(Historico.objects.filter(id=base.pk).exists())

    def test_propuesta_con_incidencia_o_sin_revision_no_se_aplica(self):
        self._escenario()
        self._punto(0, None)
        con_incidencia, _ = self._punto_propuesto(
            1, revision={"incidencia_ubicacion": True}
        )
        puntos = [
            con_incidencia,
            self._punto(2, {"latitud": "-35.1", "longitud": "-57.5"}),
            self._punto(3, self._propuesta(999999)),
        ]
        apps = _migrar(self.DESPUES)
        Punto = apps.get_model("sitios", "PuntoControl")
        for punto in puntos:
            self.assertIsNone(Punto.objects.get(pk=punto.pk).latitud)
        Historico = apps.get_model("sitios", "HistoricalPuntoControl")
        self.assertFalse(Historico.objects.filter(history_type="~").exists())

    def test_propuesta_no_finita_o_fuera_de_rango_se_omite(self):
        self._escenario()
        self._punto(0, None)
        malas = [("95", "-57.5"), ("-35.1", "-181"), ("-91", "-181")]
        puntos = [
            self._punto_propuesto(
                orden, revision={"latitud": Decimal(lat), "longitud": Decimal(lng)}
            )[0]
            for orden, (lat, lng) in enumerate(malas, start=1)
        ]
        buena, _ = self._punto_propuesto(10)
        apps = _migrar(self.DESPUES)
        Punto = apps.get_model("sitios", "PuntoControl")
        for punto in puntos:
            self.assertIsNone(Punto.objects.get(pk=punto.pk).latitud)
        self.assertEqual(Punto.objects.get(pk=buena.pk).latitud, Decimal("-35.1"))
        Historico = apps.get_model("sitios", "HistoricalPuntoControl")
        self.assertEqual(Historico.objects.filter(history_type="~").count(), 1)

    def test_revision_vieja_lejos_del_sitio_no_se_aplica(self):
        """Una revisión anterior a visitas.0008 no tiene distancia: se recalcula."""
        apps = self._escenario()
        self._punto(0, None)
        Sitio = apps.get_model("sitios", "Sitio")
        Sitio.objects.filter(pk=self.sitio.pk).update(
            latitud=Decimal("-34.0"), longitud=Decimal("-58.0")
        )
        vieja = {"distancia_m": None, "incidencia_ubicacion": False}
        lejos, _ = self._punto_propuesto(1, revision=vieja)
        cerca, _ = self._punto_propuesto(
            2,
            revision={
                **vieja,
                "latitud": Decimal("-34.0001"),
                "longitud": Decimal("-58.0001"),
            },
        )
        apps = _migrar(self.DESPUES)
        Punto = apps.get_model("sitios", "PuntoControl")
        self.assertIsNone(Punto.objects.get(pk=lejos.pk).latitud)
        self.assertIsNone(Punto.objects.get(pk=lejos.pk).longitud)
        self.assertEqual(Punto.objects.get(pk=cerca.pk).latitud, Decimal("-34.0001"))

    def test_revision_de_otro_punto_no_se_aplica(self):
        self._escenario()
        otro = self._punto(0, None)
        revision = self._revision(punto=otro)
        punto = self._punto(1, self._propuesta(revision.pk))
        apps = _migrar(self.DESPUES)
        Punto = apps.get_model("sitios", "PuntoControl")
        self.assertIsNone(Punto.objects.get(pk=punto.pk).latitud)
        Historico = apps.get_model("sitios", "HistoricalPuntoControl")
        self.assertFalse(Historico.objects.filter(history_type="~").exists())

    def test_revision_sin_precision_o_imprecisa_no_se_aplica(self):
        self._escenario()
        self._punto(0, None)
        sin_precision, _ = self._punto_propuesto(1, revision={"precision_m": None})
        imprecisa, _ = self._punto_propuesto(
            2, revision={"precision_m": settings.PRECISION_MAXIMA_M + 1}
        )
        apps = _migrar(self.DESPUES)
        Punto = apps.get_model("sitios", "PuntoControl")
        for punto in (sin_precision, imprecisa):
            self.assertIsNone(Punto.objects.get(pk=punto.pk).latitud)

    def test_coordenadas_aplicadas_salen_de_la_revision(self):
        self._escenario()
        self._punto(0, None)
        punto, _ = self._punto_propuesto(1, json={"latitud": "-10", "longitud": "-20"})
        apps = _migrar(self.DESPUES)
        Punto = apps.get_model("sitios", "PuntoControl")
        self.assertEqual(Punto.objects.get(pk=punto.pk).latitud, Decimal("-35.1"))
        self.assertEqual(Punto.objects.get(pk=punto.pk).longitud, Decimal("-57.5"))
