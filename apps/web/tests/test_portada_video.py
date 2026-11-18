"""Portada del inicio con video: atributos, precarga, script único y estáticos."""

import re
from html.parser import HTMLParser
from io import BytesIO
from wsgiref.util import setup_testing_defaults

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from whitenoise import WhiteNoise

from apps.web.models import Configuracion
from apps.web.views import primera_oracion

INSTITUCIONAL = "video-institucional-720.mp4"
VIDEOS = (
    "portada-bucle-480.mp4",
    "portada-bucle-720.mp4",
    INSTITUCIONAL,
)


class _Etiquetas(HTMLParser):
    """Lista cada etiqueta de apertura con sus atributos y la etiqueta contenedora."""

    def __init__(self):
        super().__init__()
        self.etiquetas = []  # (nombre, atributos, ancestros)
        self._pila = []

    def handle_starttag(self, nombre, atributos):
        self.etiquetas.append((nombre, dict(atributos), tuple(self._pila)))
        if nombre not in {"source", "link", "meta", "img", "br", "input"}:
            self._pila.append(nombre)

    def handle_endtag(self, nombre):
        if nombre in self._pila:
            while self._pila.pop() != nombre:
                pass


def _etiquetas(html):
    analizador = _Etiquetas()
    analizador.feed(html)
    return analizador.etiquetas


class PortadaVideoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("loaddata", "contenido_inicial", verbosity=0)

    def _inicio(self):
        return self.client.get("/").content.decode()

    def _por_nombre(self, nombre, html=None):
        return [e for e in _etiquetas(html or self._inicio()) if e[0] == nombre]

    def test_video_de_fondo_con_atributos_y_fuentes(self):
        html = self._inicio()
        self.assertIn('<section class="hero" id="hero">', html)
        fondo = next(
            e for e in self._por_nombre("video", html) if "poster" in e[1]
        )
        atributos = fondo[1]
        for atributo in ("muted", "loop", "playsinline", "autoplay"):
            self.assertIn(atributo, atributos)
        self.assertEqual(atributos["aria-hidden"], "true")
        self.assertTrue(atributos["poster"].endswith("img/portada-poster.webp"))
        fuentes = [
            e[1]
            for e in self._por_nombre("source", html)
            if "portada-bucle" in e[1]["src"]
        ]
        self.assertEqual(len(fuentes), 2)
        self.assertTrue(fuentes[0]["src"].endswith("portada-bucle-480.mp4"))
        self.assertEqual(fuentes[0]["media"], "(max-width: 900px)")
        self.assertTrue(fuentes[1]["src"].endswith("portada-bucle-720.mp4"))
        self.assertNotIn("media", fuentes[1])
        for fuente in fuentes:
            self.assertEqual(fuente["type"], "video/mp4")

    def test_poster_precargado_con_prioridad_alta(self):
        precargas = [
            e[1]
            for e in self._por_nombre("link")
            if e[1].get("rel") == "preload" and e[1].get("as") == "image"
        ]
        self.assertEqual(len(precargas), 1)
        self.assertTrue(precargas[0]["href"].endswith("img/portada-poster.webp"))
        self.assertEqual(precargas[0]["fetchpriority"], "high")

    def test_inicio_un_unico_script_externo_y_ninguno_en_linea(self):
        scripts = [e[1] for e in self._por_nombre("script")]
        externos = [s for s in scripts if "src" in s]
        self.assertEqual([s["src"] for s in externos], ["/static/js/portada.js"])
        self.assertIn("defer", externos[0])
        en_linea = [s for s in scripts if "src" not in s]
        self.assertEqual(en_linea, [{"type": "application/ld+json"}])

    def test_otras_paginas_no_cargan_el_script(self):
        for ruta in ("/empresa/", "/contacto/", "/servicio/servicio-mipu/"):
            with self.subTest(ruta=ruta):
                respuesta = self.client.get(ruta)
                self.assertEqual(respuesta.status_code, 200)
                self.assertNotIn("portada.js", respuesta.content.decode())

    def test_enlace_de_respaldo_al_video_institucional(self):
        enlaces = [
            e[1]
            for e in self._por_nombre("a")
            if INSTITUCIONAL in e[1].get("href", "")
        ]
        self.assertEqual(len(enlaces), 1)
        self.assertEqual(enlaces[0]["href"], f"/static/video/{INSTITUCIONAL}")
        self.assertIn("Ver video · 1 min", self._inicio())

    def test_video_institucional_solo_con_preload_none(self):
        apariciones = 0
        for nombre, atributos, _ in _etiquetas(self._inicio()):
            for atributo, valor in atributos.items():
                if INSTITUCIONAL not in (valor or ""):
                    continue
                if nombre == "a" and atributo == "href":
                    continue
                apariciones += 1
                self.assertEqual((nombre, atributo), ("video", "src"))
                self.assertEqual(atributos.get("preload"), "none")
                self.assertNotIn("autoplay", atributos)
        self.assertEqual(apariciones, 1)

    def test_dialogo_con_boton_de_cerrar(self):
        etiquetas = _etiquetas(self._inicio())
        dialogos = [e for e in etiquetas if e[0] == "dialog"]
        self.assertEqual(len(dialogos), 1)
        dentro = [e for e in etiquetas if "dialog" in e[2]]
        cerrar = [e[1] for e in dentro if e[0] == "button"]
        self.assertEqual(len(cerrar), 1)
        self.assertEqual(cerrar[0]["type"], "button")
        self.assertTrue(cerrar[0]["aria-label"])
        videos = [e[1] for e in dentro if e[0] == "video"]
        self.assertEqual(len(videos), 1)
        self.assertIn("controls", videos[0])
        self.assertEqual(videos[0]["preload"], "none")

    def test_boton_de_pausa_con_aria(self):
        botones = [
            e[1]
            for e in self._por_nombre("button")
            if "hero-pausa" in e[1].get("class", "")
        ]
        self.assertEqual(len(botones), 1)
        boton = botones[0]
        self.assertEqual(boton["type"], "button")
        self.assertTrue(boton["aria-label"])
        self.assertEqual(boton["aria-pressed"], "false")
        self.assertIn("hidden", boton)

    def test_parrafo_de_portada_es_la_primera_oracion(self):
        completo = Configuracion.obtener().presentacion
        esperado = primera_oracion(completo)
        self.assertTrue(completo.startswith(esperado))
        self.assertLess(len(esperado), len(completo))
        html = self._inicio()
        texto = re.search(
            r'<div class="hero-texto">.*?<p>(.*?)</p>', html, re.S
        ).group(1)
        self.assertEqual(texto, esperado)
        self.assertEqual(esperado.count(". "), 0)
        self.assertTrue(esperado.endswith("."))

    def test_primera_oracion_casos_limite(self):
        self.assertEqual(primera_oracion(""), "")
        self.assertEqual(primera_oracion("Una sola oración."), "Una sola oración.")
        self.assertEqual(primera_oracion("Sin punto final"), "Sin punto final")
        self.assertEqual(
            primera_oracion("¿Quiénes somos? Una empresa. Y más."), "¿Quiénes somos?"
        )
        self.assertEqual(
            primera_oracion("MAControl S.A. cuenta con equipo. Otra."),
            "MAControl S.A. cuenta con equipo.",
        )

    def test_javascript_servido_desde_estaticos(self):
        self.assertIsNotNone(finders.find("js/portada.js"))
        src = [e[1]["src"] for e in self._por_nombre("script") if "src" in e[1]]
        self.assertEqual(src, ["/static/js/portada.js"])


class EstaticosVideoTests(SimpleTestCase):
    def test_videos_responden_206_con_range(self):
        def app_vacia(environ, start_response):
            start_response("404 Not Found", [("Content-Type", "text/plain")])
            return [b""]

        raiz = settings.BASE_DIR / "static"
        servidor = WhiteNoise(app_vacia, root=str(raiz), prefix="static/")
        for nombre in VIDEOS:
            with self.subTest(video=nombre):
                tamano = (raiz / "video" / nombre).stat().st_size
                environ = {
                    "REQUEST_METHOD": "GET",
                    "PATH_INFO": f"/static/video/{nombre}",
                    "HTTP_RANGE": "bytes=0-1023",
                    "wsgi.input": BytesIO(),
                }
                setup_testing_defaults(environ)
                captura = {}

                def start_response(estado, cabeceras, exc_info=None):
                    captura["estado"] = estado
                    captura["cabeceras"] = dict(cabeceras)

                cuerpo = servidor(environ, start_response)
                try:
                    datos = b"".join(cuerpo)
                finally:
                    if hasattr(cuerpo, "close"):
                        cuerpo.close()
                self.assertTrue(captura["estado"].startswith("206"))
                self.assertEqual(
                    captura["cabeceras"]["Content-Range"],
                    f"bytes 0-1023/{tamano}",
                )
                self.assertEqual(len(datos), 1024)
