import re

from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import path


def _pagina_con_estilo(request):
    return HttpResponse(f'<style nonce="{request.csp_nonce}"></style>')


# Ruta de prueba: ninguna página pública lleva <style> en línea; esta sí, con el nonce.
urlpatterns = [path("base/", _pagina_con_estilo)]


class CspTests(TestCase):
    def test_cabecera_csp_presente(self):
        """La home lleva CSP con default-src 'self' y sin unsafe-inline."""
        respuesta = self.client.get("/")
        csp = respuesta["Content-Security-Policy"]
        self.assertIn("default-src 'self'", csp)
        self.assertNotIn("unsafe-inline", csp)

    @override_settings(ROOT_URLCONF=__name__)
    def test_style_lleva_el_nonce_de_la_cabecera(self):
        """El nonce de la cabecera coincide con el del <style> de la página."""
        respuesta = self.client.get("/base/")
        csp = respuesta["Content-Security-Policy"]
        en_cabecera = re.search(r"'nonce-([^']+)'", csp)
        self.assertIsNotNone(en_cabecera)
        html = respuesta.content.decode()
        en_style = re.search(r'<style nonce="([^"]+)"', html)
        self.assertIsNotNone(en_style)
        self.assertEqual(en_cabecera.group(1), en_style.group(1))

    def test_login_del_admin_lleva_csp(self):
        """El login del admin responde 200 y lleva la cabecera CSP."""
        respuesta = self.client.get("/admin/login/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("Content-Security-Policy", respuesta)

    @override_settings(ROOT_URLCONF=__name__)
    def test_nonce_cambia_en_cada_respuesta(self):
        """Dos respuestas distintas llevan nonces distintos."""
        nonces = set()
        for _ in range(2):
            csp = self.client.get("/base/")["Content-Security-Policy"]
            nonces.add(re.search(r"'nonce-([^']+)'", csp).group(1))
        self.assertEqual(len(nonces), 2)
