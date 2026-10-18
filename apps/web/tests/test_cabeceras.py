from django.test import TestCase


class ReferrerTests(TestCase):
    def test_strict_origin_when_cross_origin(self):
        """La política de Referer deja pasar el origen hacia otros orígenes."""
        respuesta = self.client.get("/")
        self.assertEqual(
            respuesta["Referrer-Policy"], "strict-origin-when-cross-origin"
        )
