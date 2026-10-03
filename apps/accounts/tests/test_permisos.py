from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, SimpleTestCase

from apps.accounts.models import User
from apps.accounts.permisos import EsAdministrador, EsEmpleado


class PermisosTests(SimpleTestCase):
    def _peticion(self, usuario):
        peticion = RequestFactory().get("/")
        peticion.user = usuario
        return peticion

    def test_es_administrador_rechaza_empleado(self):
        empleado = User(username="emp", rol=User.Rol.EMPLEADO)
        admin = User(username="adm", rol=User.Rol.ADMINISTRADOR)
        permiso = EsAdministrador()
        self.assertFalse(permiso.has_permission(self._peticion(empleado), None))
        self.assertFalse(permiso.has_permission(self._peticion(AnonymousUser()), None))
        self.assertTrue(permiso.has_permission(self._peticion(admin), None))

    def test_es_empleado_rechaza_administrador(self):
        empleado = User(username="emp", rol=User.Rol.EMPLEADO)
        admin = User(username="adm", rol=User.Rol.ADMINISTRADOR)
        permiso = EsEmpleado()
        self.assertFalse(permiso.has_permission(self._peticion(admin), None))
        self.assertFalse(permiso.has_permission(self._peticion(AnonymousUser()), None))
        self.assertTrue(permiso.has_permission(self._peticion(empleado), None))
