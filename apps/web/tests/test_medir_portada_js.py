"""Tests de la evaluación pura de `herramientas/medir_portada_js.py` (sin navegador)."""

import importlib.util
import sys
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

HERRAMIENTAS = Path(settings.BASE_DIR) / "herramientas"

BIEN = {
    "reproduce": True,
    "reducido_pausado": True,
    "pausa_fuera": True,
    "pausa_dialogo": True,
    "cerrado_pausado": True,
    "aria_pressed": ["true", "false"],
    "cerrar": (44, 44),
    "href_sin_js": "/static/video/video-institucional-720.mp4",
    "visibles_sin_js": True,
}


def _cargar_herramienta():
    sys.path.insert(0, str(HERRAMIENTAS))
    spec = importlib.util.spec_from_file_location(
        "medir_portada_js", HERRAMIENTAS / "medir_portada_js.py"
    )
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class MedirPortadaJsTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.m = _cargar_herramienta()

    def _fallas(self, **cambios):
        mediciones = self.m.evaluar_observaciones({**BIEN, **cambios})
        return [m.nombre for m in mediciones if not m.ok]

    def test_todo_en_orden_no_falla(self):
        self.assertEqual(self._fallas(), [])

    def test_falla_si_el_fondo_no_se_pausa_con_el_dialogo(self):
        self.assertEqual(
            self._fallas(pausa_dialogo=False), ["se pausa al abrir el diálogo"]
        )

    def test_falla_si_sin_js_ver_video_no_es_enlace_al_mp4(self):
        self.assertEqual(
            self._fallas(href_sin_js="#"), ["sin JS: Ver video es enlace al mp4"]
        )
