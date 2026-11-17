"""Rutas de la raíz, metadatos, JSON-LD, iconos de servicios y textos vigentes."""

import json
import re
import uuid

from django.contrib.staticfiles import finders
from django.core.management import call_command
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase
from django.views.defaults import server_error

from apps.web import iconos
from apps.web.models import Configuracion, Servicio
from apps.web.seo import datos_estructurados, json_ld


class ConContenido(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("loaddata", "contenido_inicial", verbosity=0)


class RaizTests(TestCase):
    def _comprobar(self, ruta, tipo, firma):
        respuesta = self.client.get(ruta)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Content-Type"], tipo)
        self.assertEqual(respuesta["X-Content-Type-Options"], "nosniff")
        self.assertEqual(respuesta["Cache-Control"], "public, max-age=86400")
        contenido = b"".join(respuesta.streaming_content)
        self.assertTrue(contenido.startswith(firma))
        self.assertEqual(self.client.post(ruta).status_code, 405)

    def test_favicon_ico_200(self):
        self._comprobar("/favicon.ico", "image/x-icon", b"\x00\x00\x01\x00")

    def test_apple_touch_icon_200(self):
        self._comprobar("/apple-touch-icon.png", "image/png", b"\x89PNG")

    def test_manifiesto_200_y_json(self):
        respuesta = self.client.get("/site.webmanifest")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Content-Type"], "application/manifest+json")
        datos = json.loads(respuesta.content)
        self.assertEqual(datos["short_name"], "MAControl")
        self.assertEqual(datos["start_url"], "/")
        self.assertEqual(datos["display"], "standalone")
        self.assertEqual(datos["theme_color"], "#0f1417")
        self.assertEqual(datos["background_color"], "#0f1417")
        self.assertEqual(
            sorted(i["sizes"] for i in datos["icons"]), ["192x192", "512x512"]
        )
        for icono in datos["icons"]:
            self.assertTrue(finders.find(icono["src"].removeprefix("/static/")))


class MetadatosTests(ConContenido):
    def test_og_imagen_1200x630_y_locale(self):
        html = self.client.get("/").content.decode()
        for esperado in (
            "/static/img/og-macontrol.png",
            '<meta property="og:image:width" content="1200">',
            '<meta property="og:image:height" content="630">',
            '<meta property="og:locale" content="es_AR">',
            '<meta property="og:site_name" content="MAControl S.A.">',
            '<meta name="twitter:card" content="summary_large_image">',
        ):
            self.assertIn(esperado, html)
        servicio = self.client.get("/servicio/servicio-mipu/").content.decode()
        self.assertIn("img/empresa-oficina-equipo", servicio)
        self.assertIn('<meta property="og:image:width" content="1193">', servicio)

    def test_paginas_de_error_y_qr_enlazan_iconos(self):
        paginas = {
            "404": self.client.get("/no-existe/").content.decode(),
            "500": server_error(RequestFactory().get("/boom/")).content.decode(),
            "qr": self.client.get(f"/q/{uuid.uuid4()}/").content.decode(),
        }
        for nombre, html in paginas.items():
            for esperado in ('href="/favicon.ico"', 'href="/site.webmanifest"'):
                self.assertIn(esperado, html, nombre)
        self.assertNotIn("application/ld+json", paginas["404"])


class JsonLdTests(ConContenido):
    def _bloques(self, ruta):
        html = self.client.get(ruta).content.decode()
        return re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', html, re.S
        )

    def test_inicio_trae_local_business_valido(self):
        bloques = self._bloques("/")
        self.assertEqual(len(bloques), 1)
        datos = json.loads(bloques[0])
        self.assertEqual(datos["@type"], "LocalBusiness")
        self.assertEqual(datos["name"], "MAControl S.A.")
        self.assertEqual(datos["telephone"], "+5492241546232")
        self.assertEqual(datos["taxID"], "30-71834106-6")
        self.assertEqual(datos["address"]["addressLocality"], "Castelli")
        self.assertEqual(datos["address"]["addressCountry"], "AR")
        self.assertEqual(datos["contactPoint"][0]["telephone"], "+5492241496047")
        self.assertEqual(datos["openingHoursSpecification"]["opens"], "00:00")
        self.assertEqual(len(datos["sameAs"]), 2)
        for ruta in ("/empresa/", "/contacto/", "/servicio/servicio-mipu/"):
            self.assertEqual(self._bloques(ruta), [], ruta)
        Configuracion.objects.filter(pk=1).update(atiende_24_horas=False)
        sin_24 = json.loads(self._bloques("/")[0])
        self.assertNotIn("openingHoursSpecification", sin_24)

    def test_json_ld_escapa_cierre_de_script(self):
        config = Configuracion(razon_social="</script><b>&x", pk=1)
        salida = json_ld(datos_estructurados(config))
        for peligroso in ("<", ">", "&"):
            self.assertNotIn(peligroso, salida)
        self.assertEqual(json.loads(salida)["name"], "</script><b>&x")


class IconosTests(ConContenido):
    def test_icono_por_slug_y_respaldo(self):
        self.assertEqual(len(iconos.ICONO_POR_SLUG), 9)
        for slug, trazado in iconos.ICONO_POR_SLUG.items():
            self.assertEqual(iconos.icono_de(slug), trazado)
        self.assertEqual(iconos.icono_de("servicio-nuevo"), iconos.ICONO_GENERICO)
        slugs = set(Servicio.objects.publicados().values_list("slug", flat=True))
        self.assertEqual(slugs, set(iconos.ICONO_POR_SLUG))
        html = self.client.get("/").content.decode()
        self.assertEqual(html.count('class="tarjeta-icono"'), 9)
        self.assertEqual(html.count('class="tarjeta-ver"'), 9)
        for trazado in iconos.ICONO_POR_SLUG.values():
            self.assertIn(f'<path d="{trazado}"/>', html)
        Servicio.objects.filter(slug="servicio-mipu").update(slug="servicio-otro")
        html = self.client.get("/").content.decode()
        self.assertIn(f'<path d="{iconos.ICONO_GENERICO}"/>', html)


class TextosTests(ConContenido):
    PAGINAS = ["/", "/empresa/", "/contacto/"]

    def test_ninguna_pagina_publica_trae_textos_viejos(self):
        paginas = self.PAGINAS + [
            s.get_absolute_url() for s in Servicio.objects.publicados()
        ]
        viejos = (
            "Agroindustria",
            "Hablemos",
            "espacios/sectores",
            "Naveiro",
            "Perón 427",
            "más de diez años",
            "02241 49 6047",
            "tel:+542241",
        )
        for ruta in paginas:
            html = self.client.get(ruta).content.decode()
            for texto in viejos:
                self.assertNotIn(texto, html, f"{texto!r} en {ruta}")
        inicio = self.client.get("/").content.decode()
        self.assertEqual(inicio.count("Contacto directo"), 1)
        self.assertIn("espacios y sectores", inicio)
        self.assertIn("Ministerio de Desarrollo Agrario", inicio)
        servicio = self.client.get("/servicio/servicio-mipu/").content.decode()
        self.assertIn("Ministerio de Desarrollo Agrario", servicio)
        self.assertIn("campo-imagen-portada", servicio)

    def test_inicio_trae_telefono_y_whatsapp_reales(self):
        html = self.client.get("/").content.decode()
        self.assertIn('href="tel:+5492241546232"', html)
        self.assertIn('href="https://wa.me/5492241546232"', html)
        self.assertIn("02241 15-546232", html)
        self.assertIn("franja-sectores", html)
        self.assertIn("franja-clientes", html)

    def test_segundo_telefono_en_contacto(self):
        for ruta in ("/contacto/", "/"):
            html = self.client.get(ruta).content.decode()
            self.assertIn('href="tel:+5492241496047"', html, ruta)
            self.assertIn("02241 15-496047", html, ruta)
        self.assertIn("Saavedra 555", html)
        self.assertIn("google.com/maps/search", html)
        Configuracion.objects.filter(pk=1).update(
            telefono_2="", telefono_2_internacional=""
        )
        self.assertNotIn(
            "tel:+5492241496047", self.client.get("/contacto/").content.decode()
        )

    def test_plantilla_contacto_sin_titulo_propio(self):
        html = render_to_string(
            "web/paginas/_contacto.html", {"config": Configuracion.obtener()}
        )
        self.assertNotIn("<h3", html)
