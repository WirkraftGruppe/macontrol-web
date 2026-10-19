"""El login del admin conserva el límite de fallos por IP."""

from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase

CLAVE = "clave-segura-123"
IP = "203.0.113.9"
# Mitad de una ventana de 15 min y de la de 60 min: ningún test cruza un borde.
RELOJ_FIJO = 900 * 2_000_000 + 450


class LimiteLoginAdminTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        reloj = mock.patch("config.limites.time.time", return_value=RELOJ_FIJO)
        reloj.start()
        self.addCleanup(reloj.stop)
        get_user_model().objects.create_superuser("root", password=CLAVE)

    def _ingresar(self, usuario, clave):
        return self.client.post(
            "/admin/login/",
            {"username": usuario, "password": clave},
            REMOTE_ADDR=IP,
        )

    def test_admin_bloquea_tras_fallos_por_ip(self):
        for i in range(settings.INTENTOS_FALLIDOS_POR_IP):
            self.assertEqual(self._ingresar(f"otro{i}", "mala").status_code, 200)
        respuesta = self._ingresar("root", CLAVE)
        self.assertEqual(respuesta.status_code, 429)
        self.assertNotIn("_auth_user_id", self.client.session)
