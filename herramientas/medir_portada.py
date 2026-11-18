"""Mide en el navegador la portada del inicio con video de fondo.

Uso: python herramientas/medir_portada.py [--url https://sitio] (Python del venv).
Sin --url arma una base temporal con el fixture y sirve el sitio con un servidor
WSGI con hilos que envuelve Django en WhiteNoise (el video necesita `Range`, que
runserver no atiende). Imprime una línea PASA/FALLA por medición y un resumen final;
sale con 0 solo si todas pasan. Las funciones puras (luminancia, contraste, evaluar)
no usan navegador.
"""

import argparse
import io
import os
import re
import sys
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer

sys.path.insert(0, str(Path(__file__).resolve().parent))
import humo_web as humo  # noqa: E402

VIEWPORTS = {"escritorio": (1280, 800), "móvil": (375, 812)}
SEGUNDOS = (0, 3, 7)
CONTRASTE_MINIMO = 4.5
OBJETIVO_MINIMO = 44
ELEMENTOS_TEXTO = {
    "h1": "#hero h1",
    "párrafo": "#hero .hero-texto p",
    "Llamar ahora": "#hero .btn-primario",
    "Video": "#hero #ver-video",
    "Ver servicios": "#hero .hero-botones a[href='#servicios']",
}
OCULTAR_TEXTO = (
    "#hero .hero-texto, #hero .hero-texto * { color: transparent !important; "
    "text-shadow: none !important; transition: none !important; }"
)


@dataclass(frozen=True)
class Medicion:
    nombre: str
    ok: bool
    detalle: str

    def linea(self):
        return f"{'PASA' if self.ok else 'FALLA'} {self.nombre}: {self.detalle}"


def _canal_lineal(c):
    c = c / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminancia_relativa(rgb):
    """Luminancia relativa WCAG de una tupla (r, g, b) de 0 a 255."""
    r, g, b = (_canal_lineal(c) for c in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a, b):
    """Razón de contraste WCAG entre dos colores (1 a 21)."""
    la, lb = sorted((luminancia_relativa(a), luminancia_relativa(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def componer(color, alfa, fondo):
    """Compone un color con transparencia `alfa` sobre un fondo opaco."""
    return tuple(c * alfa + f * (1 - alfa) for c, f in zip(color, fondo, strict=True))


def evaluar(nombre, valor, minimo=None, maximo=None):
    """Compara una medida con sus límites y devuelve la Medicion resultante."""
    ok = (minimo is None or valor >= minimo) and (maximo is None or valor <= maximo)
    limite = f"mínimo {minimo}" if minimo is not None else f"máximo {maximo}"
    return Medicion(nombre, ok, f"{valor:.2f} ({limite})")


def comprobar(nombre, cumple, detalle=""):
    return Medicion(nombre, bool(cumple), detalle or ("sí" if cumple else "no"))


def pixel_mas_luminoso(imagen):
    """Píxel RGB de mayor luminancia relativa de una imagen de Pillow."""
    tabla = [_canal_lineal(c) for c in range(256)]
    rgb = imagen.convert("RGB")
    leer = getattr(rgb, "get_flattened_data", rgb.getdata)
    pixeles = list(leer())
    return max(
        pixeles,
        key=lambda p: (
            0.2126 * tabla[p[0]] + 0.7152 * tabla[p[1]] + 0.0722 * tabla[p[2]]
        ),
    )


class _ServidorConHilos(ThreadingMixIn, WSGIServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        """El navegador corta conexiones de video a mitad de camino: no es un error."""


class _ManejadorSilencioso(WSGIRequestHandler):
    def log_message(self, *args):
        pass


def servir_local(entorno):
    """Levanta Django + WhiteNoise (con Range) en un hilo; devuelve (servidor, base)."""
    from whitenoise import WhiteNoise

    os.environ.update(entorno)
    sys.path.insert(0, str(humo.RAIZ))
    from django.core.wsgi import get_wsgi_application

    aplicacion = WhiteNoise(
        get_wsgi_application(), root=humo.RAIZ / "static", prefix="static/"
    )
    servidor = _ServidorConHilos(
        ("127.0.0.1", humo.puerto_libre()), _ManejadorSilencioso
    )
    servidor.set_app(aplicacion)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor, f"http://127.0.0.1:{servidor.server_port}"


def _color(texto):
    numeros = [float(n) for n in re.findall(r"[\d.]+", texto)]
    return tuple(numeros[:3]), (numeros[3] if len(numeros) > 3 else 1.0)


def _fijar_segundo(pagina, segundo):
    return pagina.evaluate(
        """async t => {
        const v = document.querySelector('#hero .hero-video'); v.pause();
        const una = ev => new Promise(r => v.addEventListener(ev, r, {once: true}));
        if (v.readyState < 2) await una('loadeddata');
        const salto = una('seeked'); v.currentTime = t;
        await Promise.race([salto, new Promise(r => setTimeout(r, 4000))]);
        return v.currentTime; }""",
        segundo,
    )


def medir_contraste(pagina, etiqueta):
    """Contraste de cada texto de la portada contra el píxel más claro bajo su caja."""
    from PIL import Image

    colores = {
        n: pagina.eval_on_selector(s, "e => getComputedStyle(e).color")
        for n, s in ELEMENTOS_TEXTO.items()
    }
    pagina.add_style_tag(content=OCULTAR_TEXTO)
    resultado = []
    for segundo in SEGUNDOS:
        real = _fijar_segundo(pagina, segundo)
        for nombre, selector in ELEMENTOS_TEXTO.items():
            caja = pagina.eval_on_selector(
                selector,
                "e => { const r = e.getBoundingClientRect();"
                " return {x: r.x + scrollX, y: r.y + scrollY,"
                " width: r.width, height: r.height}; }",
            )
            png = pagina.screenshot(clip=caja, full_page=True)
            fondo = pixel_mas_luminoso(Image.open(io.BytesIO(png)))
            rgb, alfa = _color(colores[nombre])
            valor = contraste(componer(rgb, alfa, fondo), fondo)
            medicion = evaluar(
                f"contraste {etiqueta} {nombre} s{segundo} (t={real:.1f})",
                valor,
                minimo=CONTRASTE_MINIMO,
            )
            resultado.append(medicion)
    return resultado


def medir_botones_y_objetivos(pagina, etiqueta, alto):
    """Botones visibles sin desplazar (móvil) y objetivos táctiles de al menos 44 px."""
    resultado = []
    cajas = pagina.evaluate(
        """() => Object.fromEntries([...document.querySelectorAll(
            '#hero .hero-botones a, #hero .hero-pausa')].map(e => {
            const r = e.getBoundingClientRect();
            return [e.textContent.trim() || e.className,
                {w: r.width, h: r.height, b: r.bottom}]; }))"""
    )
    for nombre, c in cajas.items():
        resultado.append(
            evaluar(
                f"objetivo {etiqueta} {nombre} ancho", c["w"], minimo=OBJETIVO_MINIMO
            )
        )
        resultado.append(
            evaluar(
                f"objetivo {etiqueta} {nombre} alto", c["h"], minimo=OBJETIVO_MINIMO
            )
        )
        if etiqueta == "móvil" and nombre in ("Llamar ahora", "Video"):
            resultado.append(
                evaluar(f"borde inferior {etiqueta} {nombre}", c["b"], maximo=alto)
            )
    return resultado


def medir_todo(navegador, base):
    mediciones = []
    for etiqueta, (ancho, alto) in VIEWPORTS.items():
        contexto = navegador.new_context(
            viewport={"width": ancho, "height": alto}, bypass_csp=True
        )
        pagina = contexto.new_page()
        pagina.goto(base + "/", wait_until="load")
        pagina.wait_for_selector("#hero .hero-pausa:not([hidden])", timeout=8000)
        mediciones += medir_botones_y_objetivos(pagina, etiqueta, alto)
        mediciones += medir_contraste(pagina, etiqueta)
        contexto.close()
    from medir_portada_js import medir_comportamiento

    return mediciones + medir_comportamiento(navegador, base)


def resumen(mediciones):
    """Línea final y código de salida: 0 solo con todas las mediciones en PASA."""
    fallas = [m for m in mediciones if not m.ok]
    if fallas:
        return f"FALLA {len(fallas)} de {len(mediciones)} mediciones", 1
    return f"PASA {len(mediciones)} mediciones", 0


def ejecutar(base):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        navegador = pw.chromium.launch(channel="chrome")
        try:
            return medir_todo(navegador, base)
        finally:
            navegador.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", help="mide ese sitio en vez de uno local")
    args = parser.parse_args()
    try:
        if args.url:
            mediciones = ejecutar(args.url.rstrip("/"))
        else:
            with tempfile.TemporaryDirectory() as carpeta:
                entorno = {
                    **{
                        k: v
                        for k, v in os.environ.items()
                        if not k.startswith("RAILWAY_") and k not in humo._NO_HEREDADAS
                    },
                    "DJANGO_SETTINGS_MODULE": "config.settings",
                    "DJANGO_ENV": "development",
                    "PYTHONIOENCODING": "utf-8",
                    "DATABASE_URL": "sqlite:///"
                    + (Path(carpeta) / "portada.sqlite3").as_posix(),
                }
                humo.django(entorno, "migrate", "--noinput")
                humo.django(entorno, "loaddata", "contenido_inicial")
                servidor, base = servir_local(entorno)
                try:
                    mediciones = ejecutar(base)
                finally:
                    servidor.shutdown()
                    servidor.server_close()
    except Exception as error:  # noqa: BLE001 - cualquier fallo de la medición es FALLA
        print(f"FALLA la medición no pudo completarse: {error}")
        return 1
    for medicion in mediciones:
        print(medicion.linea())
    texto, codigo = resumen(mediciones)
    print(texto)
    return codigo


if __name__ == "__main__":
    sys.exit(main())
