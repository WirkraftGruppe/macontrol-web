from django.contrib.auth.models import AbstractUser
from django.db import models
from simple_history.models import HistoricalRecords


class User(AbstractUser):
    """Usuario del sistema. `rol` decide el acceso al panel y a la API."""

    class Rol(models.TextChoices):
        ADMINISTRADOR = "administrador", "Administrador"
        EMPLEADO = "empleado", "Empleado"

    rol = models.CharField(
        "rol", max_length=15, choices=Rol.choices, default=Rol.EMPLEADO
    )
    telefono = models.CharField("teléfono", max_length=30, blank=True)

    history = HistoricalRecords(excluded_fields=["password", "last_login"])

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    @property
    def es_administrador(self):
        return self.rol == self.Rol.ADMINISTRADOR

    @property
    def es_empleado(self):
        return self.rol == self.Rol.EMPLEADO

    def save(self, *args, **kwargs):
        """Guarda sin historial cuando solo se actualiza `last_login` (cada login)."""
        update_fields = kwargs.get("update_fields")
        solo_last_login = update_fields is not None and set(update_fields) == {
            "last_login"
        }
        if solo_last_login:
            self.skip_history_when_saving = True
        try:
            super().save(*args, **kwargs)
        finally:
            if solo_last_login:
                del self.skip_history_when_saving
