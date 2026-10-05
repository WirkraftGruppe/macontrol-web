"""Mapa del panel: datos JSON, permisos, consultas y CSP."""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.panel.mapa import ORIGEN_TESELAS
from apps.proyectos.models import Proyecto
from apps.servicios.models import TipoServicio
from apps.sitios.models import Sitio
from apps.visitas.models import Visita

DATOS = "/panel/mapa/datos/"


class MapaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            "adm", password="clave-segura-123", rol=User.Rol.ADMINISTRADOR
        )
        cls.empleado = User.objects.create_user("emp", password="clave-segura-123")
        cls.cliente = Cliente.objects.create(razon_social="Cliente SA")
        cls.servicio = TipoServicio.objects.create(nombre="Desinsectación", slug="d")
        cls.otro_servicio = TipoServicio.objects.create(nombre="Roedores", slug="r")
        cls.hoy = timezone.localdate()

    def sitio(self, nombre="Planta", cliente=None, **campos):
        campos.setdefault("latitud", Decimal("-35.100000"))
        campos.setdefault("longitud", Decimal("-57.700000"))
        return Sitio.objects.create(
            cliente=cliente or self.cliente, nombre=nombre, **campos
        )

    def proyecto(self, sitio, dias, servicio=None, **campos):
        proxima = None if dias is None else self.hoy + timedelta(days=dias)
        return Proyecto.objects.create(
            sitio=sitio,
            tipo_servicio=servicio or self.servicio,
            titulo=f"Proyecto {sitio.nombre} {dias}",
            proxima_visita=proxima,
            encargado_inicial=self.empleado,
            encargado_actual=self.empleado,
            **campos,
        )

    def datos(self, **filtros):
        self.client.force_login(self.admin)
        respuesta = self.client.get(DATOS, filtros)
        self.assertEqual(respuesta.status_code, 200)
        return {s["nombre"]: s for s in respuesta.json()["sitios"]}

    def test_datos_colorea_por_peor_estado(self):
        mezclado = self.sitio("Mezclado")
        self.proyecto(mezclado, 60)
        self.proyecto(mezclado, -1)
        self.proyecto(mezclado, None)
        cercano = self.sitio("Cercano")
        self.proyecto(cercano, 60)
        self.proyecto(cercano, 3)
        al_dia = self.sitio("AlDia")
        self.proyecto(al_dia, 60)
        self.proyecto(al_dia, None)
        sin_fecha = self.sitio("SinFecha")
        self.proyecto(sin_fecha, None)
        self.proyecto(sin_fecha, -9, estado=Proyecto.Estado.PAUSADO)
        self.sitio("SinProyectos")
        self.sitio("Inactivo", activo=False)
        self.sitio("SinCoordenadas", latitud=None, longitud=None)

        sitios = self.datos()

        self.assertEqual(
            {n: s["estado"] for n, s in sitios.items()},
            {
                "Mezclado": "vencida",
                "Cercano": "proxima",
                "AlDia": "al_dia",
                "SinFecha": "sin_programar",
                "SinProyectos": "sin_programar",
            },
        )
        self.assertEqual(sitios["Mezclado"]["lat"], -35.1)
        self.assertEqual(sitios["Mezclado"]["lng"], -57.7)
        self.assertEqual(len(sitios["Mezclado"]["proyectos"]), 3)

    def test_datos_incluye_ultima_visita_encargado_y_ficha(self):
        sitio = self.sitio()
        proyecto = self.proyecto(sitio, 5)
        antigua = timezone.now() - timedelta(days=30)
        reciente = timezone.now() - timedelta(days=2)
        for momento in (antigua, reciente):
            Visita.objects.create(
                proyecto=proyecto,
                empleado=self.empleado,
                origen=Visita.Origen.MANUAL,
                estado=Visita.Estado.REALIZADA,
                realizada_en=momento,
            )
        Visita.objects.create(
            proyecto=proyecto, empleado=self.empleado, origen=Visita.Origen.MANUAL
        )

        sitio_json = self.datos()["Planta"]

        self.assertEqual(sitio_json["ultima_visita"], reciente.isoformat())
        self.assertEqual(sitio_json["proyectos"][0]["encargado"], "emp")
        self.assertEqual(sitio_json["proyectos"][0]["servicio"], "Desinsectación")
        # Mientras no exista la ruta de la ficha (T7), la clave es None.
        self.assertIn("url_ficha", sitio_json)

    def test_datos_filtra_por_cliente_servicio_y_estado(self):
        otro = Cliente.objects.create(razon_social="Otro SA")
        a = self.sitio("A")
        self.proyecto(a, -1)
        b = self.sitio("B", cliente=otro)
        self.proyecto(b, 60, servicio=self.otro_servicio)

        self.assertEqual(set(self.datos(cliente=otro.pk)), {"B"})
        self.assertEqual(set(self.datos(servicio=self.otro_servicio.pk)), {"B"})
        self.assertEqual(set(self.datos(estado="vencida")), {"A"})
        self.assertEqual(set(self.datos(estado="no_existe", cliente="x")), {"A", "B"})

    def test_datos_exige_administrador(self):
        self.assertEqual(self.client.get(DATOS).status_code, 302)
        self.assertEqual(self.client.get("/panel/mapa/").status_code, 302)
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get(DATOS).status_code, 403)
        self.assertEqual(self.client.get("/panel/mapa/").status_code, 403)

    def test_datos_consultas_constantes(self):
        def consultas():
            self.client.force_login(self.admin)
            with self.assertNumQueries(4):
                # sesión, usuario, sitios y proyectos prefetch
                self.client.get(DATOS)

        sitio = self.sitio("Uno")
        self.proyecto(sitio, 1)
        consultas()
        for n in range(5):
            otro = self.sitio(f"Sitio {n}")
            self.proyecto(otro, n)
            self.proyecto(otro, None)
        consultas()

    def test_mapa_permite_teselas_osm_en_csp(self):
        self.client.force_login(self.admin)
        for ruta in ("/panel/mapa/", DATOS):
            politica = self.client.get(ruta).headers["Content-Security-Policy"]
            img = next(
                d for d in politica.split(";") if d.strip().startswith("img-src")
            )
            self.assertIn(ORIGEN_TESELAS, img)
        # Las demás páginas del panel no reciben el origen de teselas.
        politica = self.client.get("/panel/").headers["Content-Security-Policy"]
        self.assertNotIn(ORIGEN_TESELAS, politica)

    def test_mapa_carga_leaflet_y_el_script_propio(self):
        self.client.force_login(self.admin)
        html = self.client.get("/panel/mapa/").content.decode()
        self.assertIn("vendor/leaflet/leaflet.js", html)
        self.assertIn("panel/mapa.js", html)
