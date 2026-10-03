"""El admin técnico solo admite superusuarios."""

from django.contrib.auth import get_user_model
from django.test import TestCase


class AdminSiteTests(TestCase):
    def test_administrador_sin_superuser_no_entra_al_admin(self):
        usuario = get_user_model().objects.create_user(
            "jefe", password="clave-larga-123", rol="administrador", is_staff=True
        )
        self.client.force_login(usuario)
        r = self.client.get("/admin/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/admin/login/", r["Location"])

    def test_superusuario_entra_al_admin(self):
        usuario = get_user_model().objects.create_superuser(
            "root", password="clave-larga-123"
        )
        self.client.force_login(usuario)
        self.assertEqual(self.client.get("/admin/").status_code, 200)
