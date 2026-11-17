"""Pruebas de la configuración de despliegue."""

import json
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class RailwayTests(SimpleTestCase):
    def test_predeploy_es_un_solo_comando(self):
        ruta = Path(settings.BASE_DIR) / "railway.json"
        comando = json.loads(ruta.read_text(encoding="utf-8"))["deploy"][
            "preDeployCommand"
        ]
        self.assertIsInstance(comando, str)
        self.assertIn("migrate --noinput", comando)
        self.assertIn("createcachetable", comando)
