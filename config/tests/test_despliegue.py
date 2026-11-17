"""Pruebas de la configuración de despliegue."""

import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


def _leer_iac():
    ruta = Path(settings.BASE_DIR) / ".railway" / "railway.ts"
    return ruta.read_text(encoding="utf-8")


class RailwayTests(SimpleTestCase):
    def test_predeploy_declarado_en_iac(self):
        lineas = re.findall(r'^\s*preDeploy: "([^"]*)",\s*$', _leer_iac(), re.M)
        self.assertEqual(len(lineas), 1)
        self.assertIn("migrate --noinput", lineas[0])
        self.assertIn("createcachetable", lineas[0])

    def test_volumen_montado_en_data(self):
        self.assertRegex(_leer_iac(), r'volumeMounts: \{ "/data": \w+ \}')

    def test_railway_json_retirado(self):
        """No queda ningún archivo de Config as Code en la raíz."""
        restantes = sorted(p.name for p in Path(settings.BASE_DIR).glob("railway.*"))
        self.assertEqual(restantes, [])
