import datetime
import uuid

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

ANTES = ("visitas", "0004_historicalvisita_incidencia_revisada_en_and_more")
DESPUES = ("visitas", "0008_ubicacion_y_administrador")


def _destino(visitas):
    """Última migración de cada app, salvo `visitas`, que se lleva a `visitas`."""
    hojas = MigrationExecutor(connection).loader.graph.leaf_nodes()
    return [visitas if nodo[0] == "visitas" else nodo for nodo in hojas]


def _migrar(destino):
    ejecutor = MigrationExecutor(connection)
    ejecutor.migrate(destino)
    return MigrationExecutor(connection).loader.project_state(destino).apps


class MigracionRevisionesTests(TransactionTestCase):
    def tearDown(self):
        ejecutor = MigrationExecutor(connection)
        ejecutor.migrate(ejecutor.loader.graph.leaf_nodes())

    def _datos_viejos(self):
        """Dos visitas realizadas (app y manual) con evidencia, y una pendiente."""
        apps = _migrar(_destino(ANTES))
        Cliente = apps.get_model("clientes", "Cliente")
        Sitio = apps.get_model("sitios", "Sitio")
        Punto = apps.get_model("sitios", "PuntoControl")
        Servicio = apps.get_model("servicios", "TipoServicio")
        Proyecto = apps.get_model("proyectos", "Proyecto")
        Usuario = apps.get_model("accounts", "User")
        Visita = apps.get_model("visitas", "Visita")
        Foto = apps.get_model("visitas", "Foto")
        Producto = apps.get_model("productos", "Producto")
        Aplicado = apps.get_model("visitas", "ProductoAplicado")

        cliente = Cliente.objects.create(razon_social="ACME")
        sitio = Sitio.objects.create(cliente=cliente, nombre="Planta 1")
        general = Punto.objects.create(sitio=sitio, nombre="General", orden=0)
        otro = Punto.objects.create(sitio=sitio, nombre="Sala", orden=1)
        servicio = Servicio.objects.create(nombre="Roedores", slug="roedores-mig")
        empleado = Usuario.objects.create(username="emp-mig", rol="empleado")
        proyecto = Proyecto.objects.create(
            sitio=sitio,
            tipo_servicio=servicio,
            titulo="Mensual",
            encargado_inicial=empleado,
            encargado_actual=empleado,
        )
        cerrada = datetime.datetime(2026, 9, 1, 12, 0, tzinfo=datetime.UTC)
        codigo = uuid.uuid4()
        app = Visita.objects.create(
            proyecto=proyecto,
            empleado=empleado,
            origen="app",
            estado="realizada",
            realizada_en=cerrada,
            latitud="-35.100000",
            longitud="-57.700000",
            precision_m="8.5",
            datos={"cebos": 3},
            esquema_planilla=[{"clave": "cebos"}],
            cliente_uuid=codigo,
            recibida_en=cerrada + datetime.timedelta(minutes=5),
        )
        manual = Visita.objects.create(
            proyecto=proyecto,
            empleado=empleado,
            origen="manual",
            motivo_manual="Carga",
            estado="realizada",
            realizada_en=cerrada,
        )
        pendiente = Visita.objects.create(
            proyecto=proyecto, empleado=empleado, origen="app"
        )
        producto = Producto.objects.create(nombre_comercial="Cebo")
        for visita in (app, manual):
            Foto.objects.create(visita=visita, imagen=f"visitas/fotos/{visita.pk}.jpg")
        Aplicado.objects.create(
            visita=app, producto=producto, lote="L1", dosis="2.5", unidad="ml"
        )
        return {
            "app": app,
            "manual": manual,
            "pendiente": pendiente,
            "general": general,
            "otro": otro,
            "codigo": codigo,
            "cerrada": cerrada,
        }

    def test_fotos_y_productos_pasan_a_revision_general(self):
        datos = self._datos_viejos()
        apps = _migrar(_destino(DESPUES))
        Visita = apps.get_model("visitas", "Visita")
        Revision = apps.get_model("visitas", "Revision")
        Foto = apps.get_model("visitas", "Foto")
        Aplicado = apps.get_model("visitas", "ProductoAplicado")

        # Una revisión por visita realizada, en el punto General (orden 0).
        self.assertEqual(Revision.objects.count(), 2)
        app = Revision.objects.get(visita_id=datos["app"].pk)
        self.assertEqual(app.punto_id, datos["general"].pk)
        self.assertEqual(app.cliente_uuid, datos["codigo"])
        self.assertEqual(str(app.latitud), "-35.100000")
        self.assertEqual(str(app.precision_m), "8.5")
        self.assertEqual(app.datos, {"cebos": 3})
        self.assertEqual(app.esquema_planilla, [{"clave": "cebos"}])
        self.assertEqual(app.realizada_en, datos["cerrada"])
        self.assertEqual(
            app.recibida_en, datos["cerrada"] + datetime.timedelta(minutes=5)
        )
        manual = Revision.objects.get(visita_id=datos["manual"].pk)
        self.assertEqual(manual.recibida_en, datos["cerrada"])
        self.assertIsNone(manual.cliente_uuid)

        # Las fotos y los productos cuelgan de la revisión.
        self.assertEqual(
            Foto.objects.get(revision=app).imagen.name,
            f"visitas/fotos/{datos['app'].pk}.jpg",
        )
        self.assertEqual(Foto.objects.filter(revision=manual).count(), 1)
        self.assertEqual(Aplicado.objects.get().revision_id, app.pk)

        # La visita conserva el cierre y deja de llevar la evidencia.
        realizada = Visita.objects.get(pk=datos["app"].pk)
        self.assertEqual(realizada.cerrada_en, datos["cerrada"])
        self.assertEqual(realizada.abierta_en, datos["cerrada"])
        self.assertEqual(realizada.cierre, "empleado")
        self.assertEqual(realizada.datos, {})
        self.assertEqual(realizada.esquema_planilla, [])
        self.assertEqual(
            Visita.objects.get(pk=datos["manual"].pk).cierre, "administrador"
        )
        pendiente = Visita.objects.get(pk=datos["pendiente"].pk)
        self.assertEqual(pendiente.estado, "pendiente")
        self.assertIsNone(pendiente.abierta_en)

    def test_pendiente_con_evidencia_queda_con_incidencia_y_no_se_cierra_sin_escaneo(
        self,
    ):
        datos = self._datos_viejos()
        apps = _migrar(_destino(ANTES))
        apps.get_model("visitas", "Foto").objects.create(
            visita_id=datos["pendiente"].pk, imagen="visitas/fotos/pendiente.jpg"
        )
        apps = _migrar(_destino(DESPUES))
        Visita = apps.get_model("visitas", "Visita")
        Revision = apps.get_model("visitas", "Revision")

        pendiente = Visita.objects.get(pk=datos["pendiente"].pk)
        self.assertEqual(pendiente.estado, "pendiente")
        self.assertEqual(Revision.objects.filter(visita=pendiente).count(), 1)
        self.assertTrue(pendiente.incidencia)
        self.assertIn(
            "Evidencia migrada de una visita pendiente", pendiente.incidencia_detalle
        )

        # Con los modelos reales: no se reutiliza y, si se abriera, no se cierra.
        from apps.accounts.models import User
        from apps.visitas.models import Visita as VisitaReal
        from apps.visitas.services import abrir_visita

        empleado = User.objects.get(pk=pendiente.empleado_id)
        real = VisitaReal.objects.get(pk=pendiente.pk)
        qr = real.proyecto.sitio.puntos.get(orden=0).qr_codigo
        abierta, _ = abrir_visita(
            empleado=empleado, proyecto=real.proyecto, qr_codigo=qr
        )
        self.assertNotEqual(abierta.pk, real.pk)

    def test_vuelta_atras_devuelve_la_evidencia_a_la_visita(self):
        datos = self._datos_viejos()
        _migrar(_destino(DESPUES))
        apps = _migrar(_destino(ANTES))
        Visita = apps.get_model("visitas", "Visita")
        Foto = apps.get_model("visitas", "Foto")
        Aplicado = apps.get_model("visitas", "ProductoAplicado")
        app = Visita.objects.get(pk=datos["app"].pk)
        self.assertEqual(app.realizada_en, datos["cerrada"])
        self.assertEqual(str(app.latitud), "-35.100000")
        self.assertEqual(app.cliente_uuid, datos["codigo"])
        self.assertEqual(app.datos, {"cebos": 3})
        self.assertEqual(Foto.objects.filter(visita=app).count(), 1)
        self.assertEqual(Aplicado.objects.get().visita_id, app.pk)
        self.assertEqual(Foto.objects.filter(visita_id=datos["manual"].pk).count(), 1)

    def test_sitio_sin_punto_recibe_uno_general(self):
        datos = self._datos_viejos()
        apps = _migrar(_destino(ANTES))
        apps.get_model("sitios", "PuntoControl").objects.all().delete()
        apps = _migrar(_destino(DESPUES))
        Revision = apps.get_model("visitas", "Revision")
        punto = apps.get_model("sitios", "PuntoControl").objects.get()
        self.assertEqual((punto.nombre, punto.orden), ("General", 0))
        self.assertEqual(Revision.objects.filter(punto_id=punto.pk).count(), 2)
        self.assertEqual(datos["app"].pk, Revision.objects.first().visita_id)
