"""Prueba de humo de la demo portátil: arranca `demo.bat` y recorre el login del panel.

Uso: python herramientas/humo_demo.py <carpeta con demo.bat>

Solo usa la biblioteca estándar. Sale con 0 si todos los chequeos pasan.
"""

import http.cookiejar
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PUERTO = 8000
BASE = f"http://localhost:{PUERTO}"
ESPERA_ARRANQUE = 120
USUARIO = "demo-admin"
CLAVE = "demo1234"


class SinRedireccion(urllib.request.HTTPRedirectHandler):
    """Evita seguir redirecciones para poder inspeccionar el 302."""

    def redirect_request(self, *args, **kwargs):
        return None


def puerto_ocupado() -> bool:
    """Indica si algo ya escucha en el puerto de la demo."""
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", PUERTO)) == 0


def esperar_servidor(proceso: subprocess.Popen) -> bool:
    """Espera hasta ESPERA_ARRANQUE segundos a que la portada responda."""
    limite = time.monotonic() + ESPERA_ARRANQUE
    while time.monotonic() < limite:
        if proceso.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(BASE + "/", timeout=5):
                return True
        except (urllib.error.URLError, OSError):
            time.sleep(2)
    return False


def informar(nombre: str, ok: bool, detalle: str = "") -> bool:
    """Imprime una línea PASA/FALLA por chequeo."""
    print(f"{'PASA' if ok else 'FALLA'}  {nombre} {detalle}".rstrip())
    return ok


def chequear_sitio() -> list[bool]:
    """Recorre portada, redirección al login, ingreso y panel."""
    resultados = []
    jar = http.cookiejar.CookieJar()
    cookies = urllib.request.HTTPCookieProcessor(jar)
    abridor = urllib.request.build_opener(cookies)
    sin_redir = urllib.request.build_opener(cookies, SinRedireccion)

    with abridor.open(BASE + "/", timeout=15) as r:
        resultados.append(informar("GET / -> 200", r.status == 200, f"({r.status})"))

    try:
        sin_redir.open(BASE + "/panel/", timeout=15)
        codigo, destino = 200, ""
    except urllib.error.HTTPError as e:
        codigo, destino = e.code, e.headers.get("Location", "")
    ok = codigo == 302 and "/panel/ingresar/" in destino
    resultados.append(
        informar("GET /panel/ sin sesión -> 302 al login", ok, f"({codigo} {destino})")
    )

    url_login = BASE + "/panel/ingresar/"
    with abridor.open(url_login, timeout=15) as r:
        html = r.read().decode("utf-8")
    token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
    resultados.append(informar("Login: formulario con token CSRF", token is not None))
    if token is None:
        return resultados
    datos = {
        "csrfmiddlewaretoken": token.group(1),
        "username": USUARIO,
        "password": CLAVE,
        "next": "/panel/",
    }
    pedido = urllib.request.Request(
        url_login,
        data=urllib.parse.urlencode(datos).encode(),
        headers={"Referer": url_login},
    )
    with abridor.open(pedido, timeout=30) as r:
        resultados.append(
            informar("POST login", r.status == 200, f"({r.status} {r.geturl()})")
        )

    with abridor.open(BASE + "/panel/", timeout=30) as r:
        cuerpo = r.read().decode("utf-8")
        en_panel = (
            r.status == 200
            and "/panel/ingresar/" not in r.geturl()
            and (not re.search(r"name=.username.", cuerpo))
        )
        resultados.append(
            informar(
                "GET /panel/ con sesión -> 200 (no es el login)",
                en_panel,
                f"({r.status})",
            )
        )
    return resultados


def main() -> int:
    """Lanza la demo, corre los chequeos y la apaga siempre."""
    if len(sys.argv) != 2:
        print("Uso: humo_demo.py <carpeta>")
        return 2
    carpeta = Path(sys.argv[1]).resolve()
    if not (carpeta / "demo.bat").is_file():
        print(f"FALLA  no existe {carpeta / 'demo.bat'}")
        return 1
    if puerto_ocupado():
        print(f"FALLA  el puerto {PUERTO} ya está ocupado; cerrá lo que lo use")
        return 1

    log = tempfile.NamedTemporaryFile("w+b", suffix=".log", delete=False)
    entorno = {**os.environ, "DEMO_SIN_NAVEGADOR": "1"}
    proceso = subprocess.Popen(
        ["cmd.exe", "/c", str(carpeta / "demo.bat")],
        cwd=carpeta,
        env=entorno,
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    resultados: list[bool] = []
    try:
        arrancó = esperar_servidor(proceso)
        resultados.append(informar(f"Arranque (hasta {ESPERA_ARRANQUE} s)", arrancó))
        if arrancó:
            resultados += chequear_sitio()
    except Exception as e:  # noqa: BLE001 - cualquier error cuenta como falla
        resultados.append(informar("Excepción durante los chequeos", False, repr(e)))
    finally:
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(proceso.pid)],
            capture_output=True,
            check=False,
        )
        time.sleep(2)
        libre = not puerto_ocupado()
        resultados.append(informar("Apagado: el puerto queda libre", libre))
        log.close()
    if not all(resultados):
        print("--- registro de demo.bat ---")
        print(Path(log.name).read_text(encoding="utf-8", errors="replace"))
    Path(log.name).unlink(missing_ok=True)
    return 0 if all(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
