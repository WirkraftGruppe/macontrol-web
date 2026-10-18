"""Pruebas del orden de las directivas de la CSP."""

from unittest import mock

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from config.csp import CSPMiddlewareOrdenado, reordenar_politica

ORDEN = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "style-src": ["'self'", "'nonce-abc'"],
        "script-src": ["'self'"],
        "img-src": ["'self'", "data:"],
    }
}
DESORDENADA = (
    "img-src 'self' data:; script-src 'self'; default-src 'self'; "
    "style-src 'self' 'nonce-abc'"
)


def _responder(request):
    return HttpResponse()


class CspOrdenadoTests(SimpleTestCase):
    def _respuesta(self, **cabeceras):
        """Pasa por el middleware una respuesta con las cabeceras dadas."""
        request = RequestFactory().get("/")
        middleware = CSPMiddlewareOrdenado(_responder)
        respuesta = HttpResponse()
        for nombre, valor in cabeceras.items():
            respuesta[nombre.replace("_", "-")] = valor
        return middleware.process_response(request, respuesta)

    def test_directivas_siguen_el_orden_de_settings(self):
        """Aunque django-csp las arme desordenadas, salen en el orden de settings."""
        with (
            override_settings(CONTENT_SECURITY_POLICY=ORDEN),
            mock.patch("csp.middleware.build_policy", return_value=DESORDENADA),
        ):
            respuesta = self._respuesta()
        self.assertEqual(
            respuesta["Content-Security-Policy"],
            "default-src 'self'; style-src 'self' 'nonce-abc'; "
            "script-src 'self'; img-src 'self' data:",
        )

    def test_reordenar_conserva_valores_y_nonce(self):
        """El conjunto de directivas y valores no cambia; las ajenas van al final."""
        entrada = DESORDENADA + "; report-uri /csp; upgrade-insecure-requests"
        salida = reordenar_politica(entrada, list(ORDEN["DIRECTIVES"]))
        self.assertEqual(
            set(salida.split("; ")), set(entrada.split("; ")), "cambió el contenido"
        )
        self.assertIn("style-src 'self' 'nonce-abc'", salida.split("; "))
        self.assertEqual(
            salida.split("; ")[-2:], ["report-uri /csp", "upgrade-insecure-requests"]
        )

    def test_report_only_sigue_su_propio_orden(self):
        """La cabecera Report-Only usa el orden de su propio setting."""
        solo_informar = {
            "DIRECTIVES": {"img-src": ["'self'"], "default-src": ["'self'"]}
        }
        with (
            override_settings(
                CONTENT_SECURITY_POLICY=ORDEN,
                CONTENT_SECURITY_POLICY_REPORT_ONLY=solo_informar,
            ),
            mock.patch("csp.middleware.build_policy", return_value=""),
        ):
            respuesta = self._respuesta(
                Content_Security_Policy_Report_Only="default-src 'self'; img-src 'self'"
            )
        self.assertEqual(
            respuesta["Content-Security-Policy-Report-Only"],
            "img-src 'self'; default-src 'self'",
        )
