"""El admin técnico solo admite superusuarios."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings


class AdminSiteTests(TestCase):
    def test_staff_sin_superuser_no_entra_al_admin(self):
        usuario = get_user_model().objects.create_user(
            "jefe", password="clave-larga-123", is_staff=True
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

    @override_settings(
        MIDDLEWARE=[
            *settings.MIDDLEWARE,
            "django.contrib.auth.middleware.LoginRequiredMiddleware",
        ]
    )
    def test_login_del_admin_no_requiere_sesion_con_login_required_middleware(self):
        self.assertEqual(self.client.get("/admin/login/").status_code, 200)
