"""Tests de las funciones puras de `herramientas/medir_portada.py` (sin navegador)."""

import importlib.util
import sys
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

HERRAMIENTAS = Path(settings.BASE_DIR) / "herramientas"


def _cargar_herramienta():
    sys.path.insert(0, str(HERRAMIENTAS))
    spec = importlib.util.spec_from_file_location(
        "medir_portada", HERRAMIENTAS / "medir_portada.py"
    )
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class MedirPortadaTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.m = _cargar_herramienta()

    def test_contraste_blanco_sobre_negro_es_21(self):
        self.assertAlmostEqual(self.m.contraste((255, 255, 255), (0, 0, 0)), 21.0)

    def test_contraste_menor_a_4_5_es_falla(self):
        valor = self.m.contraste((119, 119, 119), (255, 255, 255))
        medicion = self.m.evaluar("gris", valor, minimo=4.5)
        self.assertLess(valor, 4.5)
        self.assertFalse(medicion.ok)
        self.assertTrue(medicion.linea().startswith("FALLA"))

    def test_objetivo_tactil_menor_a_44_es_falla(self):
        self.assertFalse(self.m.evaluar("botón", 40, minimo=44).ok)
        self.assertTrue(self.m.evaluar("botón", 44, minimo=44).ok)

    def test_resumen_sale_con_1_si_alguna_falla(self):
        buenas = [self.m.comprobar("a", True)]
        self.assertEqual(self.m.resumen(buenas)[1], 0)
        self.assertEqual(self.m.resumen([*buenas, self.m.comprobar("b", False)])[1], 1)
