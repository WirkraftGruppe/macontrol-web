"""Procesamiento de fotos de visitas: reduce, corrige orientación y quita metadatos."""

import warnings
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, JpegImagePlugin, UnidentifiedImageError

LADO_MAXIMO = 1600
CALIDAD_JPEG = 85
# MPO es un JPEG con varios cuadros: Pillow lo abre con format == "MPO".
MAX_PIXELES_POR_FORMATO = {
    "JPEG": 40_000_000,
    "MPO": 40_000_000,
    "PNG": 16_000_000,
    "WEBP": 8_000_000,
}
# Un JPEG progresivo o CMYK guarda los coeficientes a resolución completa y
# draft() no los reduce: la memoria sube mucho más que con un baseline. Lo mismo
# pasa con un muestreo distinto de 4:2:2 y 4:2:0 (get_sampling fuera de 1 y 2).
MAX_PIXELES_JPEG_COSTOSO = 16_000_000


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
                tope = MAX_PIXELES_POR_FORMATO.get(original.format)
                if tope is None:
                    raise Image.DecompressionBombError("Formato sin tope.")
                if original.format in ("JPEG", "MPO") and (
                    original.info.get("progressive")
                    or original.mode == "CMYK"
                    or (
                        # Un JPEG en grises tiene un solo componente: get_sampling
                        # da -1 y draft() sí lo reduce.
                        original.mode != "L"
                        and JpegImagePlugin.get_sampling(original) not in (1, 2)
                    )
                ):
                    tope = MAX_PIXELES_JPEG_COSTOSO
                if ancho * alto > tope:
                    raise Image.DecompressionBombError("Demasiados píxeles.")
                original.draft("RGB", (LADO_MAXIMO, LADO_MAXIMO))
                # draft() no reduce una imagen muy apaisada: quedaría entera en memoria.
                if original.size[0] * original.size[1] > MAX_PIXELES_JPEG_COSTOSO:
                    raise Image.DecompressionBombError("Demasiados píxeles tras draft.")
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
        # Un zTXt/iTXt que descomprime más de MAX_TEXT_CHUNK lanza ValueError
        # en open() o en load(): es un archivo inválido, no un error del servidor.
        ValueError,
    ) as error:
        raise ValidationError("El archivo no es una imagen válida.") from error
    return ContentFile(salida.getvalue())
