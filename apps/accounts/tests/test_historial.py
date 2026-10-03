from django.test import TestCase

from apps.accounts.models import User


class HistorialUserTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user("ana", password="clave-segura-123")

    def test_historial_no_guarda_password_ni_last_login(self):
        campos = {campo.name for campo in User.history.model._meta.get_fields()}
        self.assertNotIn("password", campos)
        self.assertNotIn("last_login", campos)
        antes = User.history.filter(id=self.usuario.id).count()
        self.assertTrue(self.client.login(username="ana", password="clave-segura-123"))
        self.assertEqual(User.history.filter(id=self.usuario.id).count(), antes)
        self.usuario.refresh_from_db()
        self.assertIsNotNone(self.usuario.last_login)
        self.assertFalse(hasattr(self.usuario, "skip_history_when_saving"))

    def test_cambio_de_rol_queda_en_historial(self):
        self.usuario.rol = User.Rol.ADMINISTRADOR
        self.usuario.save()
        ultimo = User.history.filter(id=self.usuario.id).first()
        self.assertEqual(ultimo.rol, User.Rol.ADMINISTRADOR)
        self.assertEqual(User.history.filter(id=self.usuario.id).count(), 2)
