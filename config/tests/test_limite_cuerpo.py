"""Tope al tamaño del cuerpo de las peticiones."""

from django.conf import settings
from django.test import TestCase, override_settings

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "config.limite_cuerpo.LimiteCuerpoMiddleware",
    *[m for m in settings.MIDDLEWARE if "SecurityMiddleware" not in m],
]


@override_settings(MIDDLEWARE=MIDDLEWARE, LIMITE_CUERPO_BYTES=1000)
class LimiteCuerpoTests(TestCase):
    def test_post_con_content_length_excesivo_da_413_antes_de_csrf(self):
        # Sin token CSRF: si llegara a Csrf daría 403, no 413.
        r = self.client.post("/admin/login/", CONTENT_LENGTH="1001")
        self.assertEqual(r.status_code, 413)

    def test_post_dentro_del_tope_sigue_su_curso(self):
        r = self.client.post("/admin/login/", {"username": "x", "password": "y"})
        self.assertNotEqual(r.status_code, 413)
