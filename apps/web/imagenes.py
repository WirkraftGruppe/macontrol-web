"""Reprocesado de imágenes subidas al sitio: formato real, sin metadatos."""

from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

from .validators import TAMANO_MAXIMO_IMAGEN

FORMATOS_PERMITIDOS = ("JPEG", "PNG", "WEBP")


def reprocesar_imagen(archivo, *, formato_salida: str) -> ContentFile:
    """Devuelve la imagen re-codificada sin EXIF ni `info`, en JPEG o PNG.

    JPEG sale en RGB; PNG conserva el canal alfa. Lanza ValidationError si el
    formato real no es JPEG/PNG/WEBP, el archivo está corrupto o supera el tope
    de píxeles de Pillow. El tamaño se controla antes de abrir el archivo.
    """
    tamano = getattr(archivo, "size", None)
    if tamano is not None and tamano > TAMANO_MAXIMO_IMAGEN:
        raise ValidationError("La imagen no puede pesar más de 2 MB.")
    try:
        with Image.open(archivo, formats=FORMATOS_PERMITIDOS) as original:
            # Tope de píxeles leído de la cabecera, antes de decodificar: no usa los
            # filtros de `warnings`, que son estado global y no seguro entre hilos.
            limite = Image.MAX_IMAGE_PIXELS
            if limite is not None and original.width * original.height > limite:
                raise Image.DecompressionBombError("Demasiados píxeles")
            original.load()
            try:
                ImageOps.exif_transpose(original, in_place=True)
            except Exception:  # noqa: BLE001
                # La rotación es cosmética y el EXIF se descarta igual.
                pass
            if formato_salida == "PNG":
                tiene_alfa = "A" in original.mode or "transparency" in original.info
                imagen = original.convert("RGBA" if tiene_alfa else "RGB")
            else:
                imagen = original.convert("RGB")
            imagen.info = {}
            salida = BytesIO()
            imagen.save(salida, format=formato_salida)
    except Image.DecompressionBombError as error:
        raise ValidationError(
            "La imagen tiene una resolución demasiado alta; use una más chica."
        ) from error
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise ValidationError(
            "El archivo no es una imagen válida (solo JPEG, PNG o WEBP)."
        ) from error
    extension = "png" if formato_salida == "PNG" else "jpg"
    return ContentFile(salida.getvalue(), name=f"imagen.{extension}")
