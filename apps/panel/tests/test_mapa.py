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
from apps.sitios.models import PuntoControl, Sitio
from apps.visitas import services as servicios_visita
from apps.visitas.models import Revision, Visita

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

    def revisar(self, sitio, proyecto, dias_atras, punto=None):
        """Revisa un punto (por defecto el "General") hace `dias_atras` días."""
        punto = punto or sitio.puntos.get(nombre="General")
        momento = timezone.now() - timedelta(days=dias_atras)
        visita = Visita.objects.create(
            proyecto=proyecto,
            empleado=self.empleado,
            origen=Visita.Origen.APP,
            estado=Visita.Estado.REALIZADA,
            abierta_en=momento,
            cerrada_en=momento,
        )
        Revision.objects.create(
            visita=visita, punto=punto, realizada_en=momento, recibida_en=momento
        )
        return punto

    def test_muestra_atribucion_osm(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get("/panel/mapa/")

        self.assertContains(respuesta, "colaboradores de OpenStreetMap")
        self.assertContains(respuesta, "https://www.openstreetmap.org/copyright")

    def test_color_es_peor_estado_de_puntos(self):
        sitio = self.sitio("Mezclado")
        proyecto = self.proyecto(sitio, 60, frecuencia_dias=30)
        self.revisar(sitio, proyecto, 1)
        self.assertEqual(self.datos()["Mezclado"]["estado"], "al_dia")
        cercano = PuntoControl.objects.create(sitio=sitio, nombre="Cercano")
        self.revisar(sitio, proyecto, 28, cercano)
        self.assertEqual(self.datos()["Mezclado"]["estado"], "proxima")
        atrasado = PuntoControl.objects.create(sitio=sitio, nombre="Atrasado")
        self.revisar(sitio, proyecto, 40, atrasado)
        self.assertEqual(self.datos()["Mezclado"]["estado"], "vencida")
        PuntoControl.objects.create(sitio=sitio, nombre="Nuevo")
        self.assertEqual(self.datos()["Mezclado"]["estado"], "vencida")
        self.assertEqual(set(self.datos(estado="vencida")), {"Mezclado"})
        self.assertEqual(set(self.datos(estado="al_dia")), set())
        PuntoControl.objects.filter(nombre__in=["Atrasado", "Cercano"]).update(
            activo=False
        )
        self.assertEqual(self.datos()["Mezclado"]["estado"], "sin_revisar")
        self.assertEqual(set(self.datos(estado="sin_revisar")), {"Mezclado"})

    def test_datos_lista_sitios_activos_con_coordenadas(self):
        mezclado = self.sitio("Mezclado")
        self.proyecto(mezclado, 60)
        self.proyecto(mezclado, -1)
        self.proyecto(mezclado, None)
        self.sitio("SinProyectos")
        self.sitio("Inactivo", activo=False)
        self.sitio("SinCoordenadas", latitud=None, longitud=None)

        sitios = self.datos()

        # Sin proyectos con frecuencia el punto no vence; el estado de cada
        # proyecto sigue yendo en su detalle.
        self.assertEqual(
            {n: s["estado"] for n, s in sitios.items()},
            {"Mezclado": "sin_revisar", "SinProyectos": "al_dia"},
        )
        self.assertEqual(sitios["Mezclado"]["lat"], -35.1)
        self.assertEqual(sitios["Mezclado"]["lng"], -57.7)
        self.assertEqual(len(sitios["Mezclado"]["proyectos"]), 3)
        self.assertIn("vencida", {p["estado"] for p in sitios["Mezclado"]["proyectos"]})

    def test_ultima_visita_ignora_administradores(self):
        sitio = self.sitio()
        proyecto = self.proyecto(sitio, 5)
        punto = self.revisar(sitio, proyecto, 10)
        propia = timezone.now() - timedelta(days=10)
        visita, _ = servicios_visita.abrir_visita(
            empleado=self.admin, proyecto=proyecto, qr_codigo=punto.qr_codigo
        )
        Visita.objects.filter(pk=visita.pk).update(
            estado=Visita.Estado.REALIZADA, cerrada_en=timezone.now()
        )

        sitio_json = self.datos()["Planta"]

        self.assertEqual(sitio_json["ultima_visita"][:16], propia.isoformat()[:16])

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
                abierta_en=momento,
                cerrada_en=momento,
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
        self.revisar(a, self.proyecto(a, -1, frecuencia_dias=30), 40)
        b = self.sitio("B", cliente=otro)
        self.proyecto(b, 60, servicio=self.otro_servicio)

        self.assertEqual(set(self.datos(cliente=otro.pk)), {"B"})
        self.assertEqual(set(self.datos(servicio=self.otro_servicio.pk)), {"B"})
        self.assertEqual(set(self.datos(estado="vencida")), {"A"})
        self.assertEqual(set(self.datos(estado="sin_revisar")), {"B"})
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
            with self.assertNumQueries(7):
                # sesión, usuario, sitios, proyectos y puntos prefetch, y los
                # proyectos activos y revisiones de `estados_de_puntos`
                self.client.get(DATOS)

        sitio = self.sitio("Uno")
        self.revisar(sitio, self.proyecto(sitio, 1, frecuencia_dias=30), 1)
        consultas()
        for n in range(5):
            otro = self.sitio(f"Sitio {n}")
            proyecto = self.proyecto(otro, n, frecuencia_dias=30)
            self.proyecto(otro, None)
            self.revisar(otro, proyecto, n)
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
