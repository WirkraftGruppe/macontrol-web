"""Autenticación de la API: JWT, rotación, blacklist y límite de intentos."""

from django.core.cache import cache
from django.test import TestCase
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from apps.accounts.models import User

CLAVE = "clave-segura-123"
TOKEN = "/api/v1/auth/token/"
REFRESH = "/api/v1/auth/token/refresh/"


class AuthApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.usuario = User.objects.create_user("emp", password=CLAVE)

    def _pedir_token(self, clave=CLAVE):
        return self.client.post(
            TOKEN,
            {"username": "emp", "password": clave},
            content_type="application/json",
        )

    def _tokens(self):
        respuesta = self._pedir_token()
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.json()

    def _renovar(self, refresh):
        return self.client.post(
            REFRESH, {"refresh": refresh}, content_type="application/json"
        )

    def test_anonimo_recibe_401(self):
        self.assertEqual(self.client.get("/api/v1/").status_code, 401)

    def test_autenticado_recibe_su_rol(self):
        acceso = self._tokens()["access"]
        respuesta = self.client.get("/api/v1/", HTTP_AUTHORIZATION=f"Bearer {acceso}")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), {"usuario": "emp", "rol": "empleado"})

    def test_token_y_refresh_funcionan(self):
        tokens = self._tokens()
        respuesta = self._renovar(tokens["refresh"])
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("access", respuesta.json())
        self.assertIn("refresh", respuesta.json())

    def test_refresh_usado_queda_en_blacklist(self):
        refresh = self._tokens()["refresh"]
        self.assertEqual(self._renovar(refresh).status_code, 200)
        self.assertEqual(BlacklistedToken.objects.count(), 1)
        self.assertEqual(self._renovar(refresh).status_code, 401)

    def test_usuario_inactivo_no_obtiene_token(self):
        self.usuario.is_active = False
        self.usuario.save()
        self.assertEqual(self._pedir_token().status_code, 401)

    def test_refresh_de_usuario_desactivado_falla(self):
        refresh = self._tokens()["refresh"]
        self.usuario.is_active = False
        self.usuario.save()
        self.assertEqual(self._renovar(refresh).status_code, 401)

    def test_token_limita_intentos_anonimos(self):
        codigos = [self._pedir_token("mala").status_code for _ in range(11)]
        self.assertEqual(codigos[:10], [401] * 10)
        self.assertEqual(codigos[10], 429)

    def test_sesion_django_no_autentica_la_api(self):
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get("/api/v1/").status_code, 401)

    def test_refresh_tras_cambio_de_contrasena_falla(self):
        refresh = self._tokens()["refresh"]
        self.usuario.set_password("otra-clave-segura-456")
        self.usuario.save()
        self.assertEqual(self._renovar(refresh).status_code, 401)

    def test_renovar_tiene_cupo_propio(self):
        refresh = self._tokens()["refresh"]
        for _ in range(10):
            self._pedir_token("mala")
        self.assertEqual(self._pedir_token("mala").status_code, 429)
        self.assertEqual(self._renovar(refresh).status_code, 200)
