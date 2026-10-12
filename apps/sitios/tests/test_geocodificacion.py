import json
import urllib.error
from unittest import mock

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.sitios import geocodificacion

ABRIR = "apps.sitios.geocodificacion._abrir"


def _respuesta(*items):
    return json.dumps(list(items)).encode()


class GeocodificacionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.admin = User.objects.create_user(
            "adm", password="clave-segura-123", rol=User.Rol.ADMINISTRADOR
        )
        self.url = reverse("panel:sitios:geocodificar")

    def test_exige_administrador(self):
        with mock.patch(ABRIR) as abrir:
            self.assertEqual(self.client.post(self.url, {"q": "x"}).status_code, 302)
            empleado = User.objects.create_user("emp", password="clave-segura-123")
            self.client.force_login(empleado)
            self.assertEqual(self.client.post(self.url, {"q": "x"}).status_code, 403)
        abrir.assert_not_called()

    def test_solo_post_y_texto_fuera_de_la_url(self):
        self.client.force_login(self.admin)
        with mock.patch(ABRIR, return_value=b"[]") as abrir:
            self.assertEqual(self.client.get(self.url, {"q": "x"}).status_code, 405)
            abrir.assert_not_called()
            self.assertEqual(self.client.post(self.url, {"q": "x"}).status_code, 200)
        self.assertNotIn("?q=", self.url)
        cliente = self.client_class(enforce_csrf_checks=True)
        cliente.force_login(self.admin)
        self.assertEqual(cliente.post(self.url, {"q": "x"}).status_code, 403)

    def test_devuelve_candidatos_validados(self):
        datos = _respuesta(
            {"display_name": "Castelli", "lat": "-36.09", "lon": "-57.79"},
            {"display_name": "Fuera de rango", "lat": "95", "lon": "0"},
            {"display_name": "No numérico", "lat": "abc", "lon": "0"},
        )
        self.client.force_login(self.admin)
        with mock.patch(ABRIR, return_value=datos):
            r = self.client.post(self.url, {"q": "Castelli"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json()["resultados"],
            [{"nombre": "Castelli", "lat": -36.09, "lng": -57.79}],
        )

    def test_url_usa_host_fijo_y_solo_el_texto(self):
        self.client.force_login(self.admin)
        with mock.patch(ABRIR, return_value=b"[]") as abrir:
            self.client.post(self.url, {"q": "Calle 1 & x=y"})
        solicitud = abrir.call_args.args[0]
        self.assertTrue(
            solicitud.full_url.startswith(
                "https://nominatim.openstreetmap.org/search?q=calle+1+%26+x%3Dy"
            )
        )
        self.assertIn("format=jsonv2", solicitud.full_url)
        self.assertIn("limit=5", solicitud.full_url)
        self.assertEqual(solicitud.get_header("User-agent"), geocodificacion.USER_AGENT)

    def test_texto_vacio_o_largo_responde_400(self):
        self.client.force_login(self.admin)
        with mock.patch(ABRIR) as abrir:
            self.assertEqual(self.client.post(self.url, {"q": "  "}).status_code, 400)
            largo = self.client.post(self.url, {"q": "a" * 201})
            self.assertEqual(largo.status_code, 400)
        abrir.assert_not_called()

    def test_sin_red_responde_503_con_mensaje(self):
        self.client.force_login(self.admin)
        with mock.patch(ABRIR, side_effect=urllib.error.URLError("sin red")):
            r = self.client.post(self.url, {"q": "Castelli"})
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["error"], geocodificacion.MENSAJE_CARGA_MANUAL)

    def test_segunda_consulta_sale_de_la_cache(self):
        self.client.force_login(self.admin)
        datos = _respuesta({"display_name": "Castelli", "lat": "-36", "lon": "-57"})
        with mock.patch(ABRIR, return_value=datos) as abrir:
            primera = self.client.post(self.url, {"q": "Castelli"})
            segunda = self.client.post(self.url, {"q": "  CASTELLI "})
        self.assertEqual(abrir.call_count, 1)
        self.assertEqual(primera.json(), segunda.json())

    def test_limite_de_una_consulta_por_segundo(self):
        self.client.force_login(self.admin)
        with mock.patch(ABRIR, return_value=b"[]") as abrir:
            self.client.post(self.url, {"q": "uno"})
            r = self.client.post(self.url, {"q": "dos"})
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["error"], geocodificacion.MENSAJE_CARGA_MANUAL)
        self.assertEqual(abrir.call_count, 1)

    def test_formulario_de_alta_permite_teselas(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse("panel:sitios:alta"))
        self.assertIn("tile.openstreetmap.org", r["Content-Security-Policy"])
        self.assertContains(r, reverse("panel:sitios:geocodificar"))

    def test_json_muy_anidado_responde_503(self):
        self.client.force_login(self.admin)
        anidado = b"[" * 100_000
        with mock.patch(ABRIR, return_value=anidado):
            r = self.client.post(self.url, {"q": "Castelli"})
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["error"], geocodificacion.MENSAJE_CARGA_MANUAL)

    def test_user_agent_lleva_contacto(self):
        self.assertIn(settings.SITE_URL, geocodificacion.USER_AGENT)
        self.assertIn("administracion@macontrol.com.ar", geocodificacion.USER_AGENT)
        self.assertTrue(geocodificacion.USER_AGENT.startswith("MAControl/1.0 (+"))

    def test_respuesta_lenta_corta_por_tiempo_total(self):
        class Lenta:
            """Entrega un byte por lectura, sin cortar nunca por sí misma."""

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, cantidad):
                return b" "

        # Cada llamada a monotonic() avanza un segundo: se pasa de los 5 s.
        reloj = iter(range(0, 1000))
        self.client.force_login(self.admin)
        with (
            mock.patch("urllib.request.OpenerDirector.open", return_value=Lenta()),
            mock.patch.object(
                geocodificacion.time, "monotonic", side_effect=lambda: next(reloj)
            ),
        ):
            r = self.client.post(self.url, {"q": "Castelli"})
        self.assertEqual(r.status_code, 503)
