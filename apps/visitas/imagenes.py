"""Procesamiento de fotos de visitas: reduce, corrige orientación y quita EXIF."""

from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

LADO_MAXIMO = 1600
CALIDAD_JPEG = 85


def procesar_imagen(archivo) -> ContentFile:
    """Devuelve la imagen como JPEG RGB de lado mayor <= 1600 y sin metadatos EXIF."""
    with Image.open(archivo) as original:
        imagen = ImageOps.exif_transpose(original)
        imagen.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
        imagen = imagen.convert("RGB")
        salida = BytesIO()
        imagen.save(salida, format="JPEG", quality=CALIDAD_JPEG)
    return ContentFile(salida.getvalue())
