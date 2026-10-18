"""Prueba de humo del sitio: base temporal, fixture, runserver y dos GET.

Uso: python herramientas/humo_web.py (con el Python del venv). Sale con 0 solo si
`GET /` y `GET /servicio/control-plagas-urbanas/` responden 200.
"""

import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RUTAS = ["/", "/servicio/control-plagas-urbanas/"]
ESPERA_MAXIMA = 60
_NO_HEREDADAS = ("NUM_PROXIES", "ALLOWED_HOSTS", "SECRET_KEY", "MEDIA_ROOT")


def puerto_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def django(entorno, *args):
    """Corre `manage.py <args>` y falla si el comando falla."""
    subprocess.run(
        [sys.executable, "manage.py", *args], cwd=RAIZ, env=entorno, check=True
    )


def esperar(url):
    limite = time.monotonic() + ESPERA_MAXIMA
    while time.monotonic() < limite:
        try:
            with urllib.request.urlopen(url, timeout=5):
                return True
        except (urllib.error.URLError, OSError):
            time.sleep(0.5)
    return False


def apagar(proceso):
    """Mata el servidor y sus hijos (el autoreload no está, pero por las dudas)."""
    if proceso.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(proceso.pid)], capture_output=True
        )
    else:
        proceso.kill()
    proceso.wait()


def main():
    with tempfile.TemporaryDirectory() as carpeta:
        # Sin variables heredadas de un hosting ni de un shell con otra configuración.
        heredado = {
            k: v
            for k, v in os.environ.items()
            if not k.startswith("RAILWAY_") and k not in _NO_HEREDADAS
        }
        entorno = {
            **heredado,
            "DJANGO_SETTINGS_MODULE": "config.settings",
            "DJANGO_ENV": "development",
            "PYTHONIOENCODING": "utf-8",
            "DATABASE_URL": "sqlite:///" + (Path(carpeta) / "humo.sqlite3").as_posix(),
        }
        servidor = None
        try:
            django(entorno, "migrate", "--noinput")
            django(entorno, "loaddata", "contenido_inicial")
            puerto = puerto_libre()
            base = f"http://127.0.0.1:{puerto}"
            servidor = subprocess.Popen(
                [
                    sys.executable,
                    "manage.py",
                    "runserver",
                    f"127.0.0.1:{puerto}",
                    "--noreload",
                ],
                cwd=RAIZ,
                env=entorno,
            )
            if not esperar(base + "/"):
                print("El servidor no respondió a tiempo.")
                return 1
            for ruta in RUTAS:
                with urllib.request.urlopen(base + ruta, timeout=10) as respuesta:
                    print(f"GET {ruta} -> {respuesta.status}")
                    if respuesta.status != 200:
                        return 1
            return 0
        except (subprocess.CalledProcessError, urllib.error.URLError, OSError) as error:
            print(f"Falló la prueba de humo: {error}")
            return 1
        finally:
            if servidor is not None:
                apagar(servidor)


if __name__ == "__main__":
    sys.exit(main())
