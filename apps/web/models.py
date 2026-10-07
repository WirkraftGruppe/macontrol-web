"""Modelos del contenido del sitio público."""

import re

from django.db import models
from django.urls import reverse

from .validators import VALIDADORES_IMAGEN, validar_sectores


class Sector(models.TextChoices):
    """Sectores donde trabaja MAControl (Carta de Servicios)."""

    SALUD = "centros-de-salud", "Centros de salud"
    EDUCACION = "establecimientos-educativos", "Establecimientos educativos"
    ALIMENTOS = "fabricas-alimenticias", "Fábricas de productos alimenticios"
    INDUSTRIAL = "parques-industriales", "Parques industriales"
    PUERTOS = "puertos-maritimos", "Puertos marítimos"
    HOTELERIA = "hoteleria", "Hotelería"
    VERDES = "espacios-verdes", "Espacios verdes"
    GASTRONOMIA = "gastronomicos-y-comercios", "Gastronómicos y comercios en general"
    EDIFICIOS = "torres-edificios-condominios", "Torres, edificios y condominios"
    VIVIENDAS = "casas-departamentos-oficinas", "Casas, departamentos y oficinas"
    TRANSPORTE = (
        "vehiculos-de-transporte",
        "Vehículos de transporte de personas, mercaderías, inmuebles y bienes",
    )
    AVICOLA = "avicolas-y-feedlot", "Establecimientos avícolas y feedlot"


class Configuracion(models.Model):
    """Datos de contacto y presentación de la empresa (singleton, pk=1)."""

    razon_social = models.CharField("razón social", max_length=120, blank=True)
    eslogan = models.CharField("eslogan", max_length=160, blank=True)
    presentacion = models.TextField("presentación", blank=True)
    telefono = models.CharField("teléfono", max_length=40, blank=True)
    whatsapp = models.CharField("WhatsApp", max_length=40, blank=True)
    correo = models.EmailField("correo", blank=True)
    horario = models.CharField("horario de atención", max_length=160, blank=True)
    direcciones = models.JSONField(
        "direcciones",
        default=list,
        blank=True,
        help_text='Lista de {"localidad": "...", "direccion": "..."}.',
    )
    redes = models.JSONField(
        "redes sociales",
        default=list,
        blank=True,
        help_text='Lista de {"nombre": "...", "url": "..."}.',
    )

    class Meta:
        verbose_name = "configuración"
        verbose_name_plural = "configuración"

    def __str__(self):
        return self.razon_social or "Configuración del sitio"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def obtener(cls):
        """Devuelve la fila única, creándola vacía si falta."""
        return cls.objects.get_or_create(pk=1)[0]

    @staticmethod
    def _digitos(texto):
        return re.sub(r"\D", "", texto or "").lstrip("0")

    @property
    def telefono_href(self):
        """Enlace `tel:` con prefijo de país y sin el 0 inicial."""
        digitos = self._digitos(self.telefono)
        return f"tel:+54{digitos}" if digitos else ""

    @property
    def whatsapp_href(self):
        """Enlace de wa.me, o cadena vacía si no hay WhatsApp."""
        digitos = self._digitos(self.whatsapp)
        if not digitos:
            return ""
        if digitos.startswith("54"):
            digitos = digitos[2:]
        return f"https://wa.me/54{digitos}"


class PaginaServicioQuerySet(models.QuerySet):
    def publicadas(self):
        """Páginas publicadas cuyo tipo de servicio está activo."""
        return (
            self.filter(publicado=True, tipo__activo=True)
            .select_related("tipo")
            .order_by("tipo_id")
        )


class PaginaServicio(models.Model):
    """Contenido público de un tipo de servicio."""

    tipo = models.OneToOneField(
        "servicios.TipoServicio",
        on_delete=models.PROTECT,
        related_name="pagina",
        verbose_name="tipo de servicio",
    )
    titulo_seo = models.CharField("título para buscadores", max_length=160)
    resumen = models.TextField("resumen")
    problema = models.TextField("problema que resuelve")
    adicional = models.TextField("información adicional", blank=True)
    metodos = models.JSONField(
        "métodos",
        default=list,
        blank=True,
        help_text='Lista de {"titulo": "...", "descripcion": "..."}.',
    )
    faq = models.JSONField(
        "preguntas frecuentes",
        default=list,
        blank=True,
        help_text='Lista de {"pregunta": "...", "respuesta": "..."}.',
    )
    sectores = models.JSONField(
        "sectores",
        default=list,
        blank=True,
        validators=[validar_sectores],
        help_text="Lista de valores de Sector.",
    )
    imagen_portada = models.ImageField(
        "imagen de portada",
        upload_to="servicios/",
        blank=True,
        validators=VALIDADORES_IMAGEN,
    )
    publicado = models.BooleanField("publicado", default=False)

    objects = PaginaServicioQuerySet.as_manager()

    class Meta:
        verbose_name = "página de servicio"
        verbose_name_plural = "páginas de servicio"
        ordering = ["tipo_id"]

    def __str__(self):
        return self.titulo_seo

    def get_absolute_url(self):
        return reverse("web:servicio", args=[self.tipo.slug])


class ClienteDestacadoQuerySet(models.QuerySet):
    def activos(self):
        return self.filter(activo=True).order_by("orden", "nombre")


class ClienteDestacado(models.Model):
    """Cliente cuyo nombre o logo se muestra en el sitio."""

    nombre = models.CharField("nombre", max_length=120)
    logo = models.ImageField(
        "logo",
        upload_to="clientes/",
        blank=True,
        validators=VALIDADORES_IMAGEN,
    )
    orden = models.PositiveSmallIntegerField("orden", default=0)
    activo = models.BooleanField("activo", default=True)

    objects = ClienteDestacadoQuerySet.as_manager()

    class Meta:
        verbose_name = "cliente destacado"
        verbose_name_plural = "clientes destacados"
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre
