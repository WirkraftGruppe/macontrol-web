"""Mide el sitio en un viewport móvil de 375 px con Chrome y Playwright.

Uso: python herramientas/medir_movil.py (con el Python del venv). Arma una base
temporal con el fixture, levanta el servidor (como humo_web.py) y sale con 1 si hay
desborde horizontal, logo deformado, portada de más de 220 px o falta la marca de
página actual en /empresa/. Con 0 imprime las medidas.
"""

import os
import subprocess
import sys
import tempfile
import urllib.error
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import humo_web as humo  # noqa: E402

ANCHO, ALTO = 375, 812
RUTAS = ["/", "/empresa/", "/contacto/", "/servicio/control-murcielagos/"]
PROPORCION_LOGO = 3.96
TOLERANCIA_LOGO = 0.02
ALTO_MAXIMO_PORTADA = 220


def medir(pagina, base):
    """Visita las rutas y devuelve (medidas, problemas)."""
    medidas, problemas = [], []
    for ruta in RUTAS:
        pagina.goto(base + ruta, wait_until="load")
        ancho_doc = pagina.evaluate("document.documentElement.scrollWidth")
        logo = pagina.evaluate(
            """() => { const i = document.querySelector('.nav-logo img');
            const r = i && i.getBoundingClientRect();
            return r ? [r.width, r.height] : null; }"""
        )
        portada = pagina.evaluate(
            """() => { const c = document.querySelector('.campo-imagen-portada');
            return c ? c.getBoundingClientRect().height : null; }"""
        )
        actual = pagina.locator('[aria-current="page"]').count()
        medidas.append(
            f"{ruta}: scrollWidth={ancho_doc} logo={logo} portada={portada} "
            f"aria-current={actual}"
        )
        if ancho_doc > ANCHO:
            problemas.append(f"{ruta}: desborde horizontal ({ancho_doc} > {ANCHO})")
        if logo is None:
            problemas.append(f"{ruta}: no hay img en .nav-logo")
        elif abs(logo[0] / logo[1] / PROPORCION_LOGO - 1) > TOLERANCIA_LOGO:
            problemas.append(f"{ruta}: logo deformado ({logo[0]:.1f}x{logo[1]:.1f})")
        if ruta.startswith("/servicio/"):
            if portada is None:
                problemas.append(f"{ruta}: falta .campo-imagen-portada")
            elif portada > ALTO_MAXIMO_PORTADA:
                problemas.append(f"{ruta}: portada de {portada:.0f} px de alto")
        if ruta == "/empresa/" and actual == 0:
            problemas.append('/empresa/: falta [aria-current="page"]')
    return medidas, problemas


def entorno_de(carpeta):
    """Entorno de Django con una base SQLite temporal, como humo_web.py."""
    heredado = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("RAILWAY_") and k not in humo._NO_HEREDADAS
    }
    return {
        **heredado,
        "DJANGO_SETTINGS_MODULE": "config.settings",
        "DJANGO_ENV": "development",
        "PYTHONIOENCODING": "utf-8",
        "DATABASE_URL": "sqlite:///" + (Path(carpeta) / "medir.sqlite3").as_posix(),
    }


def main():
    medidas, problemas = [], []
    with tempfile.TemporaryDirectory() as carpeta:
        entorno = entorno_de(carpeta)
        servidor = None
        try:
            humo.django(entorno, "migrate", "--noinput")
            humo.django(entorno, "loaddata", "contenido_inicial")
            puerto = humo.puerto_libre()
            base = f"http://127.0.0.1:{puerto}"
            servidor = subprocess.Popen(
                [
                    sys.executable,
                    "manage.py",
                    "runserver",
                    f"127.0.0.1:{puerto}",
                    "--noreload",
                ],
                cwd=humo.RAIZ,
                env=entorno,
            )
            if not humo.esperar(base + "/"):
                print("El servidor no respondió a tiempo.")
                return 1
            with sync_playwright() as p:
                navegador = p.chromium.launch(channel="chrome")
                try:
                    pagina = navegador.new_page(
                        viewport={"width": ANCHO, "height": ALTO}
                    )
                    medidas, problemas = medir(pagina, base)
                finally:
                    navegador.close()
        except (
            subprocess.CalledProcessError,
            urllib.error.URLError,
            OSError,
            PlaywrightError,
        ) as error:
            print(f"Falló la medición: {error}")
            return 1
        finally:
            if servidor is not None:
                humo.apagar(servidor)
    if problemas:
        print("\n".join(problemas))
        return 1
    print("\n".join(medidas))
    return 0


if __name__ == "__main__":
    sys.exit(main())
