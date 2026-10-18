"""El fixture inicial trae el contenido de la Carta, sin objetos de otras apps."""

import json
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from apps.web.models import Configuracion, Servicio

RAIZ = Path(__file__).resolve().parents[3]
SLUGS = [
    "desinfeccion-sanitizacion-desodorizacion",
    "control-plagas-urbanas",
    "servicio-mipu",
    "mosquitos-vectores",
    "control-murcielagos",
    "exclusion-palomas-aves",
    "limpieza-tanques-cisternas",
    "manejo-plagas-edificios",
    "mantenimiento-edilicio",
]


class FixtureTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("loaddata", "contenido_inicial", verbosity=0)

    def test_carga_nueve_servicios_publicados(self):
        servicios = list(Servicio.objects.publicados())
        self.assertEqual(len(servicios), 9)
        self.assertEqual(Servicio.objects.count(), 9)
        self.assertEqual([s.orden for s in servicios], list(range(1, 10)))
        self.assertEqual([s.slug for s in servicios], SLUGS)

    def test_configuracion_trae_datos_legales_de_la_carta(self):
        config = Configuracion.obtener()
        self.assertEqual(
            config.habilitacion,
            "Empresa inscripta y habilitada — Ministerio de Agroindustria",
        )
        self.assertIn("10.699/88", config.ley)
        self.assertIn("Decreto Reglamentario 499/91", config.ley)
        self.assertEqual(config.director_tecnico, "")

    def test_fixture_solo_tiene_objetos_de_web(self):
        ruta = RAIZ / "apps/web/fixtures/contenido_inicial.json"
        with open(ruta, encoding="utf-8") as f:
            modelos = {o["model"] for o in json.load(f)}
        self.assertEqual(
            modelos, {"web.servicio", "web.configuracion", "web.clientedestacado"}
        )
