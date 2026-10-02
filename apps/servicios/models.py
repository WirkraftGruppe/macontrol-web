"""Modelos de Servicios: tipos de servicio y su planilla dinámica."""

from django.db import models


class TipoServicio(models.Model):
    """Servicio que ofrece la empresa; define la planilla de cada visita."""

    nombre = models.CharField("nombre", max_length=150)
    slug = models.SlugField("slug", max_length=150, unique=True)
    descripcion = models.TextField("descripción", blank=True)
    activo = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "tipo de servicio"
        verbose_name_plural = "tipos de servicio"

    def __str__(self):
        return self.nombre

    def esquema_planilla(self) -> list[dict]:
        """Esquema de la planilla ordenado por `orden`; lo consume la API."""
        return [
            {
                "clave": campo.clave,
                "etiqueta": campo.etiqueta,
                "tipo": campo.tipo,
                "opciones": campo.opciones,
                "obligatorio": campo.obligatorio,
                "ayuda": campo.ayuda,
                "orden": campo.orden,
            }
            for campo in self.campos.order_by("orden")
        ]


class CampoPlanilla(models.Model):
    """Campo de la planilla de un tipo de servicio."""

    class Tipo(models.TextChoices):
        TEXTO = "texto", "Texto"
        NUMERO = "numero", "Número"
        BOOLEANO = "booleano", "Sí/No"
        OPCION = "opcion", "Opción"
        OPCION_MULTIPLE = "opcion_multiple", "Opción múltiple"
        FECHA = "fecha", "Fecha"

    tipo_servicio = models.ForeignKey(
        TipoServicio,
        on_delete=models.CASCADE,
        related_name="campos",
        verbose_name="tipo de servicio",
    )
    orden = models.PositiveIntegerField("orden")
    etiqueta = models.CharField("etiqueta", max_length=150)
    clave = models.SlugField("clave", max_length=100)
    tipo = models.CharField("tipo", max_length=20, choices=Tipo.choices)
    opciones = models.JSONField("opciones", default=list, blank=True)
    obligatorio = models.BooleanField("obligatorio", default=False)
    ayuda = models.CharField("ayuda", max_length=255, blank=True)

    class Meta:
        verbose_name = "campo de planilla"
        verbose_name_plural = "campos de planilla"
        ordering = ["orden"]
        constraints = [
            models.UniqueConstraint(
                fields=["tipo_servicio", "clave"],
                name="campo_planilla_clave_unica_por_tipo",
            )
        ]

    def __str__(self):
        return f"{self.tipo_servicio} · {self.etiqueta}"
