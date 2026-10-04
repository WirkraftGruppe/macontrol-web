"""Esquema OpenAPI: exige autenticación y publica las rutas de dominio."""

import shutil
import tempfile

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User

RUTAS_DE_DOMINIO = (
    "/api/v1/productos/",
    "/api/v1/qr/{codigo}/resolver/",
    "/api/v1/me/visitas/",
    "/api/v1/visitas/",
    "/api/v1/me/historial/",
    "/api/v1/fotos/{codigo}/",
)


MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="schema-api-test-")


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class SchemaTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def test_schema_requiere_auth_y_lista_endpoints(self):
        """Anónimo recibe 401; con usuario, 200 y las seis rutas de dominio."""
        self.assertEqual(APIClient().get("/api/v1/schema/").status_code, 401)

        usuario = User.objects.create_user(
            "emp", password="clave-segura-123", rol=User.Rol.EMPLEADO
        )
        api = APIClient()
        api.force_authenticate(usuario)
        respuesta = api.get("/api/v1/schema/", {"format": "json"})
        self.assertEqual(respuesta.status_code, 200)
        rutas = respuesta.json()["paths"]
        for ruta in RUTAS_DE_DOMINIO:
            self.assertIn(ruta, rutas)
