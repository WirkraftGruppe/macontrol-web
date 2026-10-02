"""Modelos de Proyectos."""

from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from apps.servicios.models import TipoServicio
from apps.sitios.models import Sitio

UMBRAL_PROXIMA_DIAS = 7


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
        limit_choices_to={"rol": "empleado"},
    )
    encargado_actual = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="encargado actual",
        on_delete=models.PROTECT,
        related_name="proyectos_a_cargo",
        limit_choices_to={"rol": "empleado"},
    )
    creado = models.DateTimeField("creado", auto_now_add=True)
    actualizado = models.DateTimeField("actualizado", auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "proyecto"
        verbose_name_plural = "proyectos"
        ordering = ["sitio__nombre", "titulo"]

    def __str__(self):
        return f"{self.titulo} - {self.sitio.nombre}"

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
