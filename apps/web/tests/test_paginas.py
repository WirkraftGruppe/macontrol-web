"""Tests de las páginas públicas: home, servicio, contacto, /q/, SEO y errores."""

import re
import uuid
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import RequestFactory, TestCase
from django.views.defaults import server_error

from apps.servicios.models import TipoServicio
from apps.web.models import Configuracion, PaginaServicio, Sector

RAIZ = Path(__file__).resolve().parents[3]
SLUG_MIPU = "servicio-mipu"


class ConContenido(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("loaddata", "contenido_inicial", verbosity=0)


class HomeTests(ConContenido):
    def test_secciones_en_orden_y_sin_formularios(self):
        respuesta = self.client.get("/")
        self.assertEqual(respuesta.status_code, 200)
        html = respuesta.content.decode()
        ids = re.findall(r'<section[^>]*\bid="([a-z-]+)"', html)
        self.assertEqual(
            ids,
            ["hero", "respaldos", "servicios", "mantenimiento", "sectores",
             "como-trabajamos", "empresa", "clientes", "contacto"],
        )  # fmt: skip
        self.assertNotIn("<form", html)
        for valor, etiqueta in Sector.choices:
            self.assertContains(respuesta, etiqueta)
        self.assertEqual(
            len(
                re.findall(
                    r'href="/servicio/[a-z-]+/"',
                    html.split('id="servicios"')[1].split('id="mantenimiento"')[0],
                )
            ),
            9,
        )
        self.assertContains(respuesta, "Director técnico")
        self.assertContains(respuesta, "Matriculado")
        for nombre in (
            "Bioseguridad",
            "Vanguardia",
            "Compromiso",
            "Monitoreo",
            "Prevención",
            "ESAB",
            "La Zona",
        ):
            self.assertContains(respuesta, nombre)
        self.assertContains(respuesta, 'href="tel:+542241496047"')
        self.assertNotIn("wa.me", html)


class ServicioTests(ConContenido):
    def test_servicio_publicado_200_no_publicado_404(self):
        url = f"/servicio/{SLUG_MIPU}/"
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "El problema")
        self.assertContains(respuesta, "Gastronómicos y comercios en general")
        self.assertContains(respuesta, "img/empresa-oficina-equipo")
        PaginaServicio.objects.filter(tipo__slug=SLUG_MIPU).update(publicado=False)
        self.assertEqual(self.client.get(url).status_code, 404)
        PaginaServicio.objects.filter(tipo__slug=SLUG_MIPU).update(publicado=True)
        TipoServicio.objects.filter(slug=SLUG_MIPU).update(activo=False)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get("/servicio/no-existe/").status_code, 404)

    def test_faq_vacia_no_muestra_la_seccion(self):
        url = f"/servicio/{SLUG_MIPU}/"
        respuesta = self.client.get(url)
        self.assertNotContains(respuesta, "Preguntas frecuentes")
        self.assertNotContains(respuesta, 'class="faq"')
        PaginaServicio.objects.filter(tipo__slug=SLUG_MIPU).update(
            faq=[{"pregunta": "¿Cada cuánto?", "respuesta": "Según el plan."}]
        )
        respuesta = self.client.get(url)
        self.assertContains(respuesta, "Preguntas frecuentes")
        self.assertContains(respuesta, "¿Cada cuánto?")

    def test_sin_sectores_no_muestra_etiquetas(self):
        respuesta = self.client.get("/servicio/control-plagas-urbanas/")
        self.assertNotContains(respuesta, 'class="etiqueta"')


class ContactoTests(ConContenido):
    def test_telefono_principal_y_whatsapp_solo_si_esta_configurado(self):
        respuesta = self.client.get("/contacto/")
        self.assertContains(
            respuesta, 'class="contacto-telefono" href="tel:+542241496047"'
        )
        self.assertContains(respuesta, "Llamar ahora")
        self.assertNotContains(respuesta, "wa.me")
        self.assertNotContains(respuesta, "<form")
        Configuracion.objects.filter(pk=1).update(whatsapp="02241 15 55 1234")
        respuesta = self.client.get("/contacto/")
        self.assertContains(respuesta, 'href="https://wa.me/54224115551234"')


class QrTests(TestCase):
    def test_q_uuid_no_consulta_la_base_y_no_expone_datos(self):
        codigo = uuid.uuid4()
        with self.assertNumQueries(0):
            respuesta = self.client.get(f"/q/{codigo}/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(
            respuesta, "Punto de control de MAControl S.A. — use la app"
        )
        self.assertNotContains(respuesta, str(codigo))
        self.assertNotContains(respuesta, "tel:")


class SeoTests(ConContenido):
    def test_sitemap_robots_y_og(self):
        sitemap = self.client.get("/sitemap.xml")
        self.assertEqual(sitemap.status_code, 200)
        self.assertIn("xml", sitemap["Content-Type"])
        locs = re.findall(r"<loc>([^<]+)</loc>", sitemap.content.decode())
        base = settings.SITE_URL
        self.assertEqual(len(locs), 3 + 9)
        for ruta in ("/", "/empresa/", "/contacto/", f"/servicio/{SLUG_MIPU}/"):
            self.assertIn(base + ruta, locs)
        robots = self.client.get("/robots.txt")
        self.assertEqual(robots.status_code, 200)
        self.assertIn("text/plain", robots["Content-Type"])
        texto = robots.content.decode()
        for ruta in ("/panel/", "/api/", "/admin/", "/q/"):
            self.assertIn(f"Disallow: {ruta}\n", texto)
        self.assertIn(f"Sitemap: {base}/sitemap.xml", texto)
        for ruta in ("/", "/empresa/", "/contacto/", f"/servicio/{SLUG_MIPU}/"):
            html = self.client.get(ruta).content.decode()
            self.assertRegex(html, r'<meta name="description" content="[^"]+"')
            self.assertIn(f'<link rel="canonical" href="{base}{ruta}">', html)
            self.assertIn(f'<meta property="og:url" content="{base}{ruta}">', html)
            for propiedad in ("og:title", "og:description"):
                self.assertRegex(html, rf'<meta property="{propiedad}" content="[^"]+"')
            self.assertRegex(
                html,
                rf'<meta property="og:image" content="{re.escape(base)}/static/[^"]+"',
            )


class ErroresTests(ConContenido):
    def test_404_propia_y_500_sin_base(self):
        respuesta = self.client.get("/no-existe/")
        self.assertEqual(respuesta.status_code, 404)
        self.assertContains(respuesta, "Página no encontrada", status_code=404)
        self.assertContains(respuesta, "css/web.css", status_code=404)
        peticion = RequestFactory().get("/boom/")
        with self.assertNumQueries(0):
            error = server_error(peticion)
        self.assertEqual(error.status_code, 500)
        self.assertIn("Error del servidor", error.content.decode())
        self.assertIn("css/web.css", error.content.decode())


class PlantillasTests(TestCase):
    def test_ninguna_plantilla_publica_tiene_form_ni_presupuesto(self):
        carpetas = [RAIZ / "templates/web", RAIZ / "apps/web/templates/web/paginas"]
        archivos = [a for c in carpetas for a in c.rglob("*") if a.is_file()]
        archivos += [
            RAIZ / "apps/web/templates/404.html",
            RAIZ / "apps/web/templates/500.html",
        ]
        self.assertGreaterEqual(len(archivos), 10)
        for archivo in archivos:
            texto = archivo.read_text(encoding="utf-8").lower()
            self.assertNotIn("<form", texto, archivo)
            self.assertNotIn("presupuesto", texto, archivo)
