"""Modelos del contenido del sitio público."""

import os
import re
import uuid

from django.db import models
from django.urls import reverse

from .validators import VALIDADORES_IMAGEN, validar_sectores


def _ruta_con_uuid(carpeta, nombre_original):
    """`<carpeta>/<uuid4hex>.<ext>`: descarta el nombre que eligió quien subió."""
    extension = os.path.splitext(nombre_original)[1].lower()
    return f"{carpeta}/{uuid.uuid4().hex}{extension}"


def ruta_portada(instancia, nombre_original):
    return _ruta_con_uuid("servicios", nombre_original)


def ruta_logo(instancia, nombre_original):
    return _ruta_con_uuid("clientes", nombre_original)


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

    habilitacion = models.CharField("habilitación", max_length=200, blank=True)
    ley = models.CharField("certificación legal", max_length=240, blank=True)
    director_tecnico = models.CharField("director técnico", max_length=120, blank=True)

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
        """Devuelve la fila única, o una instancia vacía sin guardar si falta."""
        try:
            return cls.objects.get(pk=1)
        except cls.DoesNotExist:
            return cls(pk=1)

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


class ServicioQuerySet(models.QuerySet):
    def publicados(self):
        """Servicios publicados, en el orden del menú."""
        return self.filter(publicado=True).order_by("orden", "nombre")


class Servicio(models.Model):
    """Un servicio de la Carta con su página pública."""

    nombre = models.CharField("nombre", max_length=120)
    slug = models.SlugField("identificador en la URL", max_length=80, unique=True)
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
    foto = models.ImageField(
        "foto de portada",
        upload_to=ruta_portada,
        blank=True,
        validators=VALIDADORES_IMAGEN,
    )
    orden = models.PositiveSmallIntegerField("orden", default=0)
    publicado = models.BooleanField("publicado", default=False)

    objects = ServicioQuerySet.as_manager()

    class Meta:
        verbose_name = "servicio"
        verbose_name_plural = "servicios"
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse("web:servicio", args=[self.slug])


class ClienteDestacadoQuerySet(models.QuerySet):
    def activos(self):
        return self.filter(activo=True).order_by("orden", "nombre")


class ClienteDestacado(models.Model):
    """Cliente cuyo nombre o logo se muestra en el sitio."""

    nombre = models.CharField("nombre", max_length=120)
    logo = models.ImageField(
        "logo",
        upload_to=ruta_logo,
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
