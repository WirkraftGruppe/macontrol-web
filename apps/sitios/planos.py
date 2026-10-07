"""Planos de un sitio: valida, convierte el PDF y normaliza la imagen a PNG."""

import subprocess
import sys
import warnings
from io import BytesIO
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

from apps.sitios import rasterizar_pdf

TAMANO_MAXIMO = 20 * 1024 * 1024
LADO_MAXIMO = 4000
MAX_PIXELES = 40_000_000
TIEMPO_MAXIMO_PDF = 15
RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
ERROR_PDF_COMPLEJO = (
    "El PDF es demasiado complejo para convertirlo; expórtelo como PNG o JPG."
)
ERROR_PDF_ILEGIBLE = "No se pudo leer el PDF (corrupto o protegido con contraseña)."
ERROR_IMAGEN = "El archivo no es una imagen JPG, PNG ni un PDF válido."


def procesar_plano(archivo):
    """Devuelve ``(ContentFile PNG, ancho, alto)`` de un JPG, PNG o PDF.

    Lanza ``ValidationError`` si el archivo supera 20 MB, no es de un formato
    aceptado, está corrupto, es un PDF cifrado o sin páginas, o tiene demasiados
    píxeles. El PNG sale con el lado mayor de 4000 px como máximo y sin metadatos.
    """
    if getattr(archivo, "size", 0) > TAMANO_MAXIMO:
        raise ValidationError("El plano supera el máximo de 20 MB.")
    archivo.seek(0)
    datos = archivo.read(TAMANO_MAXIMO + 1)
    if len(datos) > TAMANO_MAXIMO:
        raise ValidationError("El plano supera el máximo de 20 MB.")
    if datos.lstrip()[:5] == b"%PDF-":
        imagen = _rasterizar_pdf(datos)
    else:
        imagen = _abrir_imagen(datos)
    imagen.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
    salida = BytesIO()
    imagen.save(salida, format="PNG")
    return ContentFile(salida.getvalue()), imagen.width, imagen.height


def _rasterizar_pdf(datos):
    """Primera página del PDF con el lado mayor en ``LADO_MAXIMO`` px.

    El render corre en un subproceso con tiempo máximo (``TIEMPO_MAXIMO_PDF``): un
    PDF con miles de operaciones de dibujo puede tardar minutos en pdfium.
    """
    try:
        proceso = subprocess.run(
            [sys.executable, "-m", "apps.sitios.rasterizar_pdf", str(LADO_MAXIMO)],
            input=datos,
            capture_output=True,
            timeout=TIEMPO_MAXIMO_PDF,
            check=False,
            cwd=RAIZ_PROYECTO,
        )
    except subprocess.TimeoutExpired as error:
        raise ValidationError(ERROR_PDF_COMPLEJO) from error
    if proceso.returncode == rasterizar_pdf.SIN_PAGINAS:
        raise ValidationError("El PDF no tiene páginas.")
    if proceso.returncode == rasterizar_pdf.SIN_TAMANO:
        raise ValidationError("La primera página del PDF no tiene tamaño.")
    if proceso.returncode != 0:
        raise ValidationError(ERROR_PDF_ILEGIBLE)
    try:
        with Image.open(BytesIO(proceso.stdout), formats=("PNG",)) as png:
            return png.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise ValidationError(ERROR_PDF_ILEGIBLE) from error


def _abrir_imagen(datos):
    """JPG o PNG como RGB, sin metadatos y con tope de píxeles."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(datos), formats=("JPEG", "PNG")) as original:
                if original.width * original.height > MAX_PIXELES:
                    raise Image.DecompressionBombError("Demasiados píxeles.")
                original.load()
                try:
                    ImageOps.exif_transpose(original, in_place=True)
                except Exception:  # noqa: BLE001
                    # La rotación es cosmética: un EXIF corrupto no debe dar un 500.
                    pass
                if original.mode in ("RGBA", "LA", "P"):
                    original = original.convert("RGBA")
                    fondo = Image.new("RGBA", original.size, "white")
                    original = Image.alpha_composite(fondo, original)
                imagen = original.convert("RGB")
                imagen.info = {}
                return imagen
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ValidationError(
            "La imagen tiene una resolución demasiado alta; use una más chica."
        ) from error
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise ValidationError(ERROR_IMAGEN) from error
