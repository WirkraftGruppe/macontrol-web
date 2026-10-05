"""Planos de un sitio: valida, convierte el PDF y normaliza la imagen a PNG."""

import warnings
from io import BytesIO

import pypdfium2
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

TAMANO_MAXIMO = 20 * 1024 * 1024
LADO_MAXIMO = 4000
MAX_PIXELES = 40_000_000
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
    """Primera página del PDF con el lado mayor en ``LADO_MAXIMO`` px."""
    try:
        documento = pypdfium2.PdfDocument(datos)
        try:
            if len(documento) == 0:
                raise ValidationError("El PDF no tiene páginas.")
            pagina = documento[0]
            ancho, alto = pagina.get_size()
            if min(ancho, alto) <= 0:
                raise ValidationError("La primera página del PDF no tiene tamaño.")
            escala = LADO_MAXIMO / max(ancho, alto)
            return pagina.render(scale=escala).to_pil().convert("RGB")
        finally:
            documento.close()
    except pypdfium2.PdfiumError as error:
        raise ValidationError(
            "No se pudo leer el PDF (corrupto o protegido con contraseña)."
        ) from error


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
