"""Recorrido de un visitante por el sitio, siguiendo los enlaces del HTML."""

import re
import uuid

from django.core.management import call_command
from django.test import TestCase


def enlaces(html, patron):
    return list(dict.fromkeys(re.findall(rf'href="({patron})"', html)))


class RecorridoPublicoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("loaddata", "contenido_inicial", verbosity=0)

    def test_visitante_recorre_el_sitio(self):
        inicio = self.client.get("/")
        self.assertEqual(inicio.status_code, 200)
        html = inicio.content.decode()
        servicios = enlaces(html, r"/servicio/[a-z0-9-]+/")
        self.assertGreaterEqual(len(servicios), 3)
        for url in servicios[:3]:
            pagina = self.client.get(url)
            self.assertEqual(pagina.status_code, 200, url)
            self.assertContains(pagina, "<h1>")
        enlace_empresa = enlaces(html, r"/empresa/")
        enlace_contacto = enlaces(html, r"/contacto/")
        self.assertEqual(len(enlace_empresa), 1)
        self.assertEqual(len(enlace_contacto), 1)
        empresa = self.client.get(enlace_empresa[0])
        self.assertEqual(empresa.status_code, 200)
        self.assertContains(empresa, "Bioseguridad")
        contacto = self.client.get(enlace_contacto[0])
        self.assertEqual(contacto.status_code, 200)
        self.assertContains(contacto, "tel:+542241496047")
        qr = self.client.get(f"/q/{uuid.uuid4()}/")
        self.assertEqual(qr.status_code, 200)
        self.assertContains(qr, "use la app")
