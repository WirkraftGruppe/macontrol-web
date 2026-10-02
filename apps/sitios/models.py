"""Modelos de Sitios."""

import uuid

from django.db import models
from simple_history.models import HistoricalRecords

from apps.clientes.models import Cliente


class Sitio(models.Model):
    """Lugar físico de un cliente donde se realizan visitas; tiene un QR propio."""

    class Sector(models.TextChoices):
        INDUSTRIA = "industria", "Industria"
        PUERTO = "puerto", "Puerto"
        GASTRONOMIA = "gastronomia", "Gastronomía"
        HOTELERIA = "hoteleria", "Hotelería"
        EDIFICIO = "edificio", "Edificio"
        SALUD = "salud", "Salud"
        EDUCACION = "educacion", "Educación"
        RURAL = "rural", "Rural"
        ESPACIO_VERDE = "espacio_verde", "Espacio verde"
        TRANSPORTE = "transporte", "Transporte"
        HOGAR = "hogar", "Hogar"
        OTRO = "otro", "Otro"

    cliente = models.ForeignKey(
        Cliente,
        verbose_name="cliente",
        on_delete=models.PROTECT,
        related_name="sitios",
    )
    nombre = models.CharField("nombre", max_length=200)
    direccion = models.CharField("dirección", max_length=255, blank=True)
    localidad = models.CharField("localidad", max_length=100, blank=True)
    latitud = models.DecimalField(
        "latitud", max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitud = models.DecimalField(
        "longitud", max_digits=9, decimal_places=6, null=True, blank=True
    )
    sector = models.CharField(
        "sector", max_length=20, choices=Sector.choices, default=Sector.OTRO
    )
    contacto_en_sitio = models.CharField(
        "contacto en el sitio", max_length=150, blank=True
    )
    telefono_en_sitio = models.CharField(
        "teléfono en el sitio", max_length=30, blank=True
    )
    horario_acceso = models.CharField("horario de acceso", max_length=200, blank=True)
    notas = models.TextField("notas", blank=True)
    qr_codigo = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    qr_impreso_el = models.DateField("QR impreso el", null=True, blank=True)
    activo = models.BooleanField("activo", default=True)
    creado = models.DateTimeField("creado", auto_now_add=True)
    actualizado = models.DateTimeField("actualizado", auto_now=True)

    history = HistoricalRecords(excluded_fields=["contacto_en_sitio", "telefono_en_sitio"])  # noqa: E501

    class Meta:
        verbose_name = "sitio"
        verbose_name_plural = "sitios"
        ordering = ["cliente__razon_social", "nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.cliente})"
