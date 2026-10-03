"""Procesamiento de fotos de visitas: reduce, corrige orientación y quita metadatos."""

import warnings
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

LADO_MAXIMO = 1600
CALIDAD_JPEG = 85
MAX_PIXELES_POR_FORMATO = {"JPEG": 40_000_000, "PNG": 16_000_000, "WEBP": 16_000_000}


def procesar_imagen(archivo) -> ContentFile:
    """Devuelve la imagen como JPEG RGB de lado mayor <= 1600 y sin metadatos.

    Lanza ValidationError si el archivo no es una imagen, su formato no es
    JPEG/PNG/WEBP, está corrupto o supera MAX_PIXELES_POR_FORMATO.
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(archivo, formats=("JPEG", "PNG", "WEBP")) as original:
                ancho, alto = original.size
                if ancho * alto > MAX_PIXELES_POR_FORMATO[original.format]:
                    raise Image.DecompressionBombError("Demasiados píxeles.")
                original.draft("RGB", (LADO_MAXIMO, LADO_MAXIMO))
                # Datos corruptos lanzan OSError acá, fuera del try del EXIF.
                original.load()
                try:
                    ImageOps.exif_transpose(original, in_place=True)
                except Exception:  # noqa: BLE001
                    # La rotación es cosmética y el EXIF se descarta igual: un EXIF
                    # corrupto (struct.error, SyntaxError, etc.) no debe dar un 500.
                    pass
                original.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
                imagen = original.convert("RGB")
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
