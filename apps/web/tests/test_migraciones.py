"""Migración de datos 0003: carga el Adjunto A sobre la base existente."""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class MigracionDatosTests(TransactionTestCase):
    antes = [("web", "0002_configuracion_datos_empresa")]
    despues = [("web", "0003_datos_adjunto_a")]

    def tearDown(self):
        self._migrar(self.despues)

    def _migrar(self, destino):
        ejecutor = MigrationExecutor(connection)
        ejecutor.migrate(destino)
        return ejecutor.loader.project_state(destino).apps

    def test_0003_carga_adjunto_a(self):
        apps = self._migrar(self.antes)
        apps.get_model("web", "Configuracion").objects.create(
            pk=1,
            telefono="02241 49 6047",
            presentacion="Somos una empresa con más de diez años en el mercado.",
            direcciones=[{"localidad": "Castelli", "direccion": "Ricardo Naveiro 7"}],
        )
        Servicio = apps.get_model("web", "Servicio")
        for slug, nombre in (
            ("servicio-mipu", "Servicio MIPU (Manejo Integral de Plagas Urbanas)"),
            ("mosquitos-vectores", "Mosquitos vectores — erradicación y prevención"),
        ):
            Servicio.objects.create(
                slug=slug,
                nombre=nombre,
                titulo_seo="Título SEO original",
                resumen="Programa de monitoreo.",
                problema="p",
            )
        apps = self._migrar(self.despues)
        config = apps.get_model("web", "Configuracion").objects.get(pk=1)
        self.assertEqual(config.cuit, "30-71834106-6")
        self.assertEqual(config.telefono, "02241 15-546232")
        self.assertEqual(config.telefono_internacional, "+5492241546232")
        self.assertEqual(config.telefono_2_internacional, "+5492241496047")
        self.assertEqual(config.whatsapp, "+5492241546232")
        self.assertEqual(config.director_tecnico, "Miguel Canale")
        self.assertTrue(config.atiende_24_horas)
        self.assertEqual(config.direcciones[0]["direccion"], "Saavedra 555")
        self.assertEqual(len(config.direcciones), 1)
        self.assertEqual(
            config.redes,
            [
                {
                    "nombre": "Instagram",
                    "url": "https://www.instagram.com/macontrol_s.a/",
                },
                {
                    "nombre": "Facebook",
                    "url": "https://www.facebook.com/share/19pND5YUct/",
                },
            ],
        )
        self.assertIn("15 años", config.presentacion)
        self.assertNotIn("más de diez años", config.presentacion)
        Servicio = apps.get_model("web", "Servicio")
        mipu = Servicio.objects.get(slug="servicio-mipu")
        self.assertEqual(mipu.nombre, "Servicio MIPU")
        self.assertEqual(
            mipu.resumen,
            "Manejo Integral de Plagas Urbanas (MIPU): Programa de monitoreo.",
        )
        self.assertEqual(mipu.titulo_seo, "Título SEO original")
        self.assertEqual(
            Servicio.objects.get(slug="mosquitos-vectores").nombre,
            "Control de mosquitos vectores",
        )

    def test_0003_sin_configuracion_no_crea_fila(self):
        self._migrar(self.antes)
        apps = self._migrar(self.despues)
        self.assertEqual(apps.get_model("web", "Configuracion").objects.count(), 0)


class PruebaDespliegueTests(TransactionTestCase):
    antes = [("web", "0003_datos_adjunto_a")]
    despues = [("web", "0004_prueba_despliegue")]

    def tearDown(self):
        self._migrar(self.despues)

    def _migrar(self, destino):
        ejecutor = MigrationExecutor(connection)
        ejecutor.migrate(destino)
        return ejecutor.loader.project_state(destino).apps

    def test_0004_es_reversible(self):
        self._migrar(self.antes)
        self._migrar(self.despues)

    def test_0004_no_cambia_filas(self):
        apps = self._migrar(self.antes)
        apps.get_model("web", "Configuracion").objects.create(pk=1, telefono="1")
        apps.get_model("web", "Servicio").objects.create(
            slug="s", nombre="S", titulo_seo="t", resumen="r", problema="p"
        )
        ClienteDestacado = apps.get_model("web", "ClienteDestacado")
        ClienteDestacado.objects.create(nombre="C")
        modelos = ("Configuracion", "Servicio", "ClienteDestacado")

        def contar(apps):
            return [apps.get_model("web", m).objects.count() for m in modelos]

        antes = contar(apps)
        self.assertEqual(antes, [1, 1, 1])
        self.assertEqual(contar(self._migrar(self.despues)), antes)
