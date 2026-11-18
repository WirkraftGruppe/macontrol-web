"""Tests de `herramientas/medir_descargas.py` (descargas concurrentes)."""

import importlib.util
import io
import re
import socket
import threading
import time
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

HERRAMIENTA = Path(settings.BASE_DIR) / "herramientas/medir_descargas.py"
TAMANO = 40 * 1024
LINEA_PAGINA = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d pagina (\d{3}) \d+$")
LINEA_DESCARGA = re.compile(r"^descarga (\d+) (\d+)/(\d+) ([\d.]+)$")


def _cargar_herramienta():
    spec = importlib.util.spec_from_file_location("medir_descargas", HERRAMIENTA)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class _Manejador(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/video":
            self._responder(TAMANO, b"x" * TAMANO)
        elif self.path == "/truncado":
            # Anuncia más bytes de los que envía y corta la conexión.
            self._responder(TAMANO, b"x" * (TAMANO // 2))
        elif self.path == "/sin-largo":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"x" * 100)
        else:
            if self.path == "/lenta":
                time.sleep(0.3)
            self._responder(2, b"ok")

    def _responder(self, largo, cuerpo):
        self.send_response(200)
        self.send_header("Content-Length", str(largo))
        self.end_headers()
        self.wfile.write(cuerpo)
        self.close_connection = True

    def log_message(self, *args):
        pass


class MedirDescargasTests(SimpleTestCase):
    def setUp(self):
        self.medir = _cargar_herramienta()
        self.servidor = ThreadingHTTPServer(("127.0.0.1", 0), _Manejador)
        self.base = f"http://127.0.0.1:{self.servidor.server_port}"
        hilo = threading.Thread(target=self.servidor.serve_forever, daemon=True)
        hilo.start()

    def tearDown(self):
        self.servidor.shutdown()
        self.servidor.server_close()

    def _ejecutar(self, video="/video", pagina="/", extra=()):
        argv = [
            "--pagina", pagina if pagina.startswith("http") else self.base + pagina,
            "--video", self.base + video,
            "--kbps", "100",
            "--cada", "0.1",
            *extra,
        ]  # fmt: skip
        salida = io.StringIO()
        with redirect_stdout(salida), redirect_stderr(io.StringIO()):
            codigo = self.medir.main(argv)
        return codigo, salida.getvalue().splitlines()

    def test_pasa_con_servidor_concurrente(self):
        codigo, lineas = self._ejecutar()
        self.assertEqual(codigo, 0, lineas)
        self.assertEqual(lineas[-1].split(" ")[0], "PASA")
        descargas = [m for m in map(LINEA_DESCARGA.match, lineas) if m]
        self.assertEqual(len(descargas), 4)
        for m in descargas:
            self.assertEqual(m.group(2), str(TAMANO))
            self.assertEqual(m.group(3), str(TAMANO))
        paginas = [m for m in map(LINEA_PAGINA.match, lineas) if m]
        self.assertTrue(paginas)
        self.assertTrue(all(m.group(1) == "200" for m in paginas))

    def test_falla_si_una_descarga_queda_incompleta(self):
        codigo, lineas = self._ejecutar(video="/truncado")
        self.assertEqual(codigo, 1)
        self.assertEqual(lineas[-1].split(" ")[0], "FALLA")

    def test_falla_si_falta_content_length(self):
        codigo, lineas = self._ejecutar(video="/sin-largo")
        self.assertEqual(codigo, 1)
        self.assertEqual(lineas[-1].split(" ")[0], "FALLA")

    def test_falla_si_la_pagina_supera_el_limite(self):
        codigo, lineas = self._ejecutar(pagina="/lenta", extra=["--limite", "0.1"])
        self.assertEqual(codigo, 1)
        self.assertEqual(lineas[-1].split(" ")[0], "FALLA")

    def test_respeta_el_limite_de_velocidad(self):
        codigo, lineas = self._ejecutar(extra=["--descargas", "1"])
        self.assertEqual(codigo, 0, lineas)
        m = next(m for m in map(LINEA_DESCARGA.match, lineas) if m)
        # 40 KB a 100 KB/s no pueden tardar menos de ~0,4 s.
        self.assertGreaterEqual(float(m.group(4)), 0.35)

    def test_pide_la_pagina_mientras_hay_descargas(self):
        _, lineas = self._ejecutar()
        paginas = [m for m in map(LINEA_PAGINA.match, lineas) if m]
        self.assertGreaterEqual(len(paginas), 2)

    def test_error_de_conexion_de_la_pagina_es_000(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            puerto = sock.getsockname()[1]
        codigo, lineas = self._ejecutar(pagina=f"http://127.0.0.1:{puerto}/")
        self.assertEqual(codigo, 1)
        self.assertIn(" pagina 000 ", lineas[0])
