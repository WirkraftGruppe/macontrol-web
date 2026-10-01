import uuid

from django.test import TestCase


class RutasTests(TestCase):
    """Las rutas provisorias responden sin exponer datos."""

    def test_raiz_responde_200(self):
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_q_uuid_responde_200(self):
        codigo = uuid.uuid4()
        respuesta = self.client.get(f"/q/{codigo}/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Sitio de MAControl S.A. — use la app")
        self.assertNotContains(respuesta, str(codigo))

    def test_q_no_uuid_da_404(self):
        self.assertEqual(self.client.get("/q/no-es-uuid/").status_code, 404)

    def test_panel_responde_200(self):
        self.assertEqual(self.client.get("/panel/").status_code, 200)

    def test_api_v1_responde_200(self):
        self.assertEqual(self.client.get("/api/v1/").status_code, 200)
