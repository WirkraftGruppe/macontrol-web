"""Acceso al panel: login, roles y salida."""

import re

from django.core.cache import cache
from django.test import TestCase
from django.urls import URLResolver, get_resolver

from apps.accounts.models import User
from apps.panel import urls

CLAVE = "clave-segura-123"


class AccesoPanelTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.admin = User.objects.create_user(
            "adm", password=CLAVE, rol=User.Rol.ADMINISTRADOR
        )
        self.empleado = User.objects.create_user("emp", password=CLAVE)

    def test_anonimo_redirige_al_login(self):
        respuesta = self.client.get("/panel/")
        self.assertRedirects(
            respuesta, "/panel/ingresar/?next=/panel/", fetch_redirect_response=False
        )

    def test_empleado_recibe_403(self):
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get("/panel/").status_code, 403)

    def test_administrador_recibe_200(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/panel/").status_code, 200)

    def test_administrador_inicia_sesion_y_entra(self):
        respuesta = self.client.post(
            "/panel/ingresar/", {"username": "adm", "password": CLAVE}
        )
        self.assertRedirects(respuesta, "/panel/", fetch_redirect_response=False)

    def test_empleado_no_inicia_sesion_en_el_panel(self):
        respuesta = self.client.post(
            "/panel/ingresar/", {"username": "emp", "password": CLAVE}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Esta cuenta no tiene acceso al panel.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_salir_cierra_la_sesion(self):
        self.client.force_login(self.admin)
        respuesta = self.client.post("/panel/salir/")
        self.assertRedirects(
            respuesta, "/panel/ingresar/", fetch_redirect_response=False
        )
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(self.client.get("/panel/salir/").status_code, 405)

    def _ingresar(self, usuario, clave):
        return self.client.post(
            "/panel/ingresar/", {"username": usuario, "password": clave}
        )

    def test_ingreso_limita_intentos_fallidos(self):
        codigos = [self._ingresar("adm", "mala").status_code for _ in range(6)]
        self.assertEqual(codigos[:5], [200] * 5)
        self.assertEqual(codigos[5], 429)
        self.assertEqual(self._ingresar("adm", CLAVE).status_code, 429)

    def test_ingreso_limitado_no_confirma_clave_de_empleado(self):
        for _ in range(5):
            self._ingresar("emp", "mala")
        respuesta = self._ingresar("emp", CLAVE)
        self.assertEqual(respuesta.status_code, 429)
        self.assertNotContains(respuesta, "no tiene acceso", status_code=429)


def _rutas_del_panel(patrones, prefijo=""):
    """Recorre los patrones del namespace `panel` y arma una URL de ejemplo por ruta."""
    for patron in patrones:
        texto = prefijo + str(patron.pattern)
        if isinstance(patron, URLResolver):
            yield from _rutas_del_panel(patron.url_patterns, texto)
        else:
            ruta = re.sub(
                r"<(?:uuid:)\w+>",
                "00000000-0000-0000-0000-000000000001",
                texto,
            )
            yield "/panel/" + re.sub(r"<(?:\w+:)?\w+>", "1", ruta)


class AccesoTests(TestCase):
    def test_empleado_no_ve_ninguna_ruta_del_panel(self):
        User.objects.create_user("emp", password=CLAVE)
        self.client.login(username="emp", password=CLAVE)
        rutas = [
            ruta
            for ruta in _rutas_del_panel(get_resolver(urls).url_patterns)
            if ruta not in ("/panel/ingresar/", "/panel/salir/")
        ]

        self.assertIn("/panel/", rutas)
        self.assertIn("/panel/mapa/", rutas)
        self.assertIn("/panel/mapa/datos/", rutas)
        for app in ("sitios", "clientes", "servicios", "proyectos", "productos"):
            self.assertIn(f"/panel/{app}/", rutas)
        self.assertIn("/panel/usuarios/", rutas)
        for ruta in rutas:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 403)
