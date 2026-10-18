"""Páginas públicas armadas desde `Servicio` y `Configuracion`."""

from django.core.management import call_command
from django.test import TestCase

from apps.web.models import Configuracion, Servicio


class PaginasPublicasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("loaddata", "contenido_inicial", verbosity=0)

    def test_cada_servicio_del_fixture_y_las_paginas_fijas_dan_200(self):
        rutas = ["/", "/empresa/", "/contacto/", "/sitemap.xml", "/robots.txt"]
        rutas += [s.get_absolute_url() for s in Servicio.objects.all()]
        self.assertEqual(len(rutas), 5 + 9)
        for ruta in rutas:
            self.assertEqual(self.client.get(ruta).status_code, 200, ruta)

    def test_servicio_con_publicado_falso_da_404_y_sale_del_menu(self):
        servicio = Servicio.objects.get(slug="servicio-mipu")
        url = servicio.get_absolute_url()
        self.assertContains(self.client.get("/empresa/"), url)
        Servicio.objects.filter(pk=servicio.pk).update(publicado=False)
        self.assertEqual(self.client.get(url).status_code, 404)
        for ruta in ("/", "/empresa/", "/sitemap.xml"):
            self.assertNotContains(self.client.get(ruta), url)

    def test_empresa_muestra_datos_legales_de_configuracion(self):
        respuesta = self.client.get("/empresa/")
        self.assertContains(respuesta, "<li>Director técnico matriculado</li>")
        self.assertContains(
            respuesta,
            "<li>Empresa inscripta y habilitada — Ministerio de Agroindustria</li>",
        )
        self.assertContains(respuesta, "Ley de Agroquímicos 10.699/88</li>")
        Configuracion.objects.filter(pk=1).update(
            habilitacion="Habilitación X", ley="Ley Y", director_tecnico="Ana Pérez"
        )
        respuesta = self.client.get("/empresa/")
        self.assertContains(respuesta, "<li>Director técnico: Ana Pérez</li>")
        self.assertContains(respuesta, "<li>Habilitación X</li>")
        self.assertContains(respuesta, "<li>Ley Y</li>")
        self.assertNotContains(respuesta, "Director técnico matriculado")
