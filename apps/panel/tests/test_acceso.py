"""Acceso al panel: login, roles y salida."""

import re

from django.core.cache import cache
from django.test import TestCase
from django.urls import URLResolver, get_resolver

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.panel import urls
from apps.proyectos.models import Proyecto
from apps.servicios.models import TipoServicio
from apps.sitios.models import Sitio

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


def _rutas_del_panel(patrones, prefijo="", pk="1"):
    """Recorre los patrones del namespace `panel` y arma una URL de ejemplo por ruta."""
    for patron in patrones:
        texto = prefijo + str(patron.pattern)
        if isinstance(patron, URLResolver):
            yield from _rutas_del_panel(patron.url_patterns, texto, pk)
        else:
            ruta = re.sub(
                r"<(?:uuid:)\w+>",
                "00000000-0000-0000-0000-000000000001",
                texto,
            )
            yield "/panel/" + re.sub(r"<(?:\w+:)?\w+>", pk, ruta)


def _rutas_protegidas(pk="1"):
    """Todas las rutas del panel salvo ingresar y salir, con `pk` en los parámetros."""
    return [
        ruta
        for ruta in _rutas_del_panel(get_resolver(urls).url_patterns, pk=pk)
        if ruta not in ("/panel/ingresar/", "/panel/salir/")
    ]


class AccesoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        """Objetos reales: las rutas con pk llegan a una vista que sí los encuentra."""
        cls.cliente = Cliente.objects.create(razon_social="Cliente SA")
        cls.sitio = Sitio.objects.create(cliente=cls.cliente, nombre="Planta")
        cls.servicio = TipoServicio.objects.create(nombre="Desinsectación", slug="d")
        cls.empleado = User.objects.create_user("emp", password=CLAVE)
        cls.proyecto = Proyecto.objects.create(
            sitio=cls.sitio,
            tipo_servicio=cls.servicio,
            titulo="Proyecto",
            encargado_inicial=cls.empleado,
            encargado_actual=cls.empleado,
        )

    def test_empleado_no_ve_ninguna_ruta_del_panel(self):
        self.client.login(username="emp", password=CLAVE)
        rutas = _rutas_protegidas()

        self.assertIn("/panel/", rutas)
        self.assertIn("/panel/mapa/", rutas)
        self.assertIn("/panel/mapa/datos/", rutas)
        for app in ("sitios", "clientes", "servicios", "proyectos", "productos"):
            self.assertIn(f"/panel/{app}/", rutas)
        self.assertIn("/panel/usuarios/", rutas)
        # GET y POST, con un pk existente y con uno inexistente: el rol se comprueba
        # antes de buscar el objeto, así la respuesta no revela qué ids existen.
        for ruta in rutas + _rutas_protegidas(pk="999999"):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 403)
                self.assertEqual(self.client.post(ruta).status_code, 403)

    def test_empleado_no_ve_rutas_con_objetos_reales(self):
        self.client.login(username="emp", password=CLAVE)
        pk = str(self.cliente.pk)
        # El id de ejemplo existe en las tablas a las que apuntan las rutas con pk.
        self.assertTrue(Proyecto.objects.filter(pk=pk).exists())
        self.assertTrue(Sitio.objects.filter(pk=pk).exists())
        for ruta in _rutas_protegidas(pk=pk):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 403)
                self.assertEqual(self.client.post(ruta).status_code, 403)

    def test_anonimo_post_va_al_login(self):
        for ruta in _rutas_protegidas(pk=str(self.cliente.pk)):
            with self.subTest(ruta=ruta):
                respuesta = self.client.post(ruta)
                self.assertEqual(respuesta.status_code, 302)
                self.assertTrue(respuesta["Location"].startswith("/panel/ingresar/"))

    def test_anonimo_va_al_login_en_todas_las_rutas(self):
        for ruta in _rutas_protegidas() + _rutas_protegidas(pk="999999"):
            with self.subTest(ruta=ruta):
                respuesta = self.client.get(ruta)
                self.assertEqual(respuesta.status_code, 302)
                self.assertTrue(respuesta["Location"].startswith("/panel/ingresar/"))
