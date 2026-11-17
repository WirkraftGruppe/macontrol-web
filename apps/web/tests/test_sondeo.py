"""Tests de la herramienta de sondeo (`herramientas/sondear.py`)."""

import importlib.util
import io
import re
import socket
import threading
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

HERRAMIENTA = Path(settings.BASE_DIR) / "herramientas/sondear.py"
LINEA = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d (\d{3}) \d+$")


def _cargar_herramienta():
    spec = importlib.util.spec_from_file_location("sondear", HERRAMIENTA)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class _Manejador(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/redireccion":
            self.send_response(302)
            self.send_header("Location", "/ok")
        else:
            self.send_response(500 if self.path == "/error" else 200)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args):
        pass


class SondeoTests(SimpleTestCase):
    def setUp(self):
        self.sondear = _cargar_herramienta()
        self.servidor = ThreadingHTTPServer(("127.0.0.1", 0), _Manejador)
        self.base = f"http://127.0.0.1:{self.servidor.server_port}"
        hilo = threading.Thread(target=self.servidor.serve_forever, daemon=True)
        hilo.start()

    def tearDown(self):
        self.servidor.shutdown()
        self.servidor.server_close()

    def _ejecutar(self, url):
        salida = io.StringIO()
        with redirect_stdout(salida), redirect_stderr(io.StringIO()):
            codigo = self.sondear.main([url, "--cada", "0.05", "--durante", "0.2"])
        return codigo, salida.getvalue().splitlines()

    def test_sale_con_cero_si_todas_las_respuestas_son_200(self):
        codigo, lineas = self._ejecutar(self.base + "/ok")
        self.assertEqual(codigo, 0)
        self.assertTrue(lineas)
        for linea in lineas:
            coincide = LINEA.match(linea)
            self.assertIsNotNone(coincide, linea)
            self.assertEqual(coincide.group(1), "200")

    def test_sale_con_uno_si_aparece_un_500(self):
        codigo, lineas = self._ejecutar(self.base + "/error")
        self.assertEqual(codigo, 1)
        self.assertTrue(all(" 500 " in linea for linea in lineas))

    def test_no_sigue_redirecciones(self):
        codigo, lineas = self._ejecutar(self.base + "/redireccion")
        self.assertEqual(codigo, 1)
        self.assertTrue(lineas)
        self.assertTrue(all(" 302 " in linea for linea in lineas))

    def test_error_de_conexion_se_registra_como_000(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            puerto = sock.getsockname()[1]
        codigo, lineas = self._ejecutar(f"http://127.0.0.1:{puerto}/")
        self.assertEqual(codigo, 1)
        self.assertTrue(lineas)
        self.assertTrue(all(" 000 " in linea for linea in lineas))
