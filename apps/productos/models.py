from django.db import models


class Producto(models.Model):
    """Producto del catálogo; las aplicaciones de las visitas siempre apuntan acá."""

    nombre_comercial = models.CharField("nombre comercial", max_length=150)
    principio_activo = models.CharField("principio activo", max_length=150, blank=True)
    registro = models.CharField(
        "registro",
        max_length=60,
        blank=True,
        help_text="Número de registro ANMAT/SENASA del producto.",
    )
    presentacion = models.CharField("presentación", max_length=100, blank=True)
    unidad_dosis_por_defecto = models.CharField(
        "unidad de dosis por defecto",
        max_length=20,
        blank=True,
        help_text="Por ejemplo: ml/l.",
    )
    activo = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "producto"
        verbose_name_plural = "productos"
        ordering = ["nombre_comercial"]

    def __str__(self):
        return self.nombre_comercial
