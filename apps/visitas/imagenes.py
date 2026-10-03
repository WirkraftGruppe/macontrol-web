"""Procesamiento de fotos de visitas: reduce, corrige orientación y quita metadatos."""

import warnings
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

LADO_MAXIMO = 1600
CALIDAD_JPEG = 85
MAX_PIXELES = 40_000_000


def procesar_imagen(archivo) -> ContentFile:
    """Devuelve la imagen como JPEG RGB de lado mayor <= 1600 y sin metadatos.

    Lanza ValidationError si el archivo no es una imagen o supera MAX_PIXELES.
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(archivo) as original:
                ancho, alto = original.size
                if ancho * alto > MAX_PIXELES:
                    raise Image.DecompressionBombError("Demasiados píxeles.")
                original.draft("RGB", (LADO_MAXIMO, LADO_MAXIMO))
                imagen = ImageOps.exif_transpose(original)
                imagen.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
                imagen = imagen.convert("RGB")
                imagen.info = {}
                salida = BytesIO()
                imagen.save(salida, format="JPEG", quality=CALIDAD_JPEG)
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as error:
        raise ValidationError("El archivo no es una imagen válida.") from error
    return ContentFile(salida.getvalue())
