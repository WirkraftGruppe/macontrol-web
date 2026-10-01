from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Usuario del sistema. `rol` decide el acceso; `is_staff` solo habilita /admin/."""

    class Rol(models.TextChoices):
        ADMINISTRADOR = "administrador", "Administrador"
        EMPLEADO = "empleado", "Empleado"

    rol = models.CharField(
        "rol", max_length=15, choices=Rol.choices, default=Rol.EMPLEADO
    )
    telefono = models.CharField("teléfono", max_length=30, blank=True)

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    @property
    def es_administrador(self):
        return self.rol == self.Rol.ADMINISTRADOR

    @property
    def es_empleado(self):
        return self.rol == self.Rol.EMPLEADO
