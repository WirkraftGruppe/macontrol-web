"""Modelos de Proyectos."""

from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from apps.accounts.models import User
from apps.servicios.models import TipoServicio
from apps.sitios.models import Sitio

UMBRAL_PROXIMA_DIAS = 7
FILTRO_ENCARGADO = {"rol": User.Rol.EMPLEADO, "is_active": True}


class EstadoVisita(models.TextChoices):
    """Situación de la próxima visita de un proyecto (usada para colorear el mapa)."""

    AL_DIA = "al_dia", "Al día"
    PROXIMA = "proxima", "Próxima a vencer"
    VENCIDA = "vencida", "Vencida"
    SIN_PROGRAMAR = "sin_programar", "Sin programar"


class Proyecto(models.Model):
    """Trabajo recurrente de un tipo de servicio en un sitio."""

    class Estado(models.TextChoices):
        ACTIVO = "activo", "Activo"
        PAUSADO = "pausado", "Pausado"
        FINALIZADO = "finalizado", "Finalizado"

    sitio = models.ForeignKey(
        Sitio,
        verbose_name="sitio",
        on_delete=models.PROTECT,
        related_name="proyectos",
    )
    tipo_servicio = models.ForeignKey(
        TipoServicio,
        verbose_name="tipo de servicio",
        on_delete=models.PROTECT,
        related_name="proyectos",
    )
    titulo = models.CharField("título", max_length=200)
    detalle = models.TextField("detalle", blank=True)
    estado = models.CharField(
        "estado", max_length=12, choices=Estado.choices, default=Estado.ACTIVO
    )
    frecuencia_dias = models.PositiveIntegerField(
        "frecuencia (días)", null=True, blank=True
    )
    proxima_visita = models.DateField("próxima visita", null=True, blank=True)
    encargado_inicial = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="encargado inicial",
        on_delete=models.PROTECT,
        related_name="proyectos_iniciados",
        limit_choices_to=FILTRO_ENCARGADO,
    )
    encargado_actual = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="encargado actual",
        on_delete=models.PROTECT,
        related_name="proyectos_a_cargo",
        limit_choices_to=FILTRO_ENCARGADO,
    )
    creado = models.DateTimeField("creado", auto_now_add=True)
    actualizado = models.DateTimeField("actualizado", auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "proyecto"
        verbose_name_plural = "proyectos"
        ordering = ["sitio__nombre", "titulo"]

    def save(self, *args, **kwargs):
        """Valida que los encargados que se asignan sean empleados activos.

        El encargado inicial se fija al crear, y dar de baja o cambiar de rol
        a un empleado ya asignado no debe bloquear guardados posteriores (por
        ejemplo, el flujo de visita guarda el proyecto). Por eso solo se
        validan los encargados nuevos o los que cambiaron.
        """
        campos = ("encargado_inicial", "encargado_actual")
        if self._state.adding:
            a_validar = campos
        else:
            guardado = (
                Proyecto.objects.filter(pk=self.pk)
                .values("encargado_inicial_id", "encargado_actual_id")
                .first()
            )
            a_validar = [
                campo
                for campo in campos
                if guardado is None
                or guardado[f"{campo}_id"] != getattr(self, f"{campo}_id")
            ]
        for campo in a_validar:
            self._meta.get_field(campo).validate(getattr(self, f"{campo}_id"), self)
        super().save(*args, **kwargs)

    def __str__(self):
        try:
            return f"{self.titulo} - {self.sitio.nombre}"
        except Sitio.DoesNotExist:
            return f"{self.titulo} - (sitio suprimido)"

    @property
    def estado_visita(self):
        """Clasifica la próxima visita según la fecha de hoy."""
        if self.proxima_visita is None:
            return EstadoVisita.SIN_PROGRAMAR
        hoy = timezone.localdate()
        if self.proxima_visita < hoy:
            return EstadoVisita.VENCIDA
        if self.proxima_visita <= hoy + timedelta(days=UMBRAL_PROXIMA_DIAS):
            return EstadoVisita.PROXIMA
        return EstadoVisita.AL_DIA
