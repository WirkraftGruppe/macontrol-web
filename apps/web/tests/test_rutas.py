import uuid

from django.test import TestCase
from django.urls import NoReverseMatch, reverse


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

    def test_panel_anonimo_redirige_al_login(self):
        respuesta = self.client.get("/panel/")
        self.assertRedirects(
            respuesta, "/panel/ingresar/?next=/panel/", fetch_redirect_response=False
        )

    def test_api_v1_anonimo_recibe_401(self):
        self.assertEqual(self.client.get("/api/v1/").status_code, 401)

    def test_rutas_con_espacio_de_nombres(self):
        codigo = uuid.uuid4()
        self.assertEqual(reverse("web:inicio"), "/")
        self.assertEqual(reverse("panel:inicio"), "/panel/")
        self.assertEqual(reverse("api:raiz"), "/api/v1/")
        self.assertEqual(reverse("web:qr", args=[codigo]), f"/q/{codigo}/")

    def test_inicio_sin_espacio_de_nombres_no_resuelve(self):
        with self.assertRaises(NoReverseMatch):
            reverse("inicio")
