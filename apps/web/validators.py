"""Validadores de los modelos del sitio público."""

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

EXTENSIONES_IMAGEN = ["png", "jpg", "jpeg", "webp"]
TAMANO_MAXIMO_IMAGEN = 2 * 1024 * 1024

validar_extension_imagen = FileExtensionValidator(allowed_extensions=EXTENSIONES_IMAGEN)


def validar_tamano_imagen(archivo):
    """Rechaza imágenes de más de 2 MB."""
    if archivo.size > TAMANO_MAXIMO_IMAGEN:
        raise ValidationError(
            "La imagen no puede pesar más de 2 MB.", code="imagen_grande"
        )


VALIDADORES_IMAGEN = [validar_extension_imagen, validar_tamano_imagen]


def validar_sectores(valor):
    """Exige una lista de valores válidos de `Sector`, sin repetidos."""
    from .models import Sector

    if not isinstance(valor, list):
        raise ValidationError(
            "Los sectores deben ser una lista.", code="sectores_formato"
        )
    invalidos = [v for v in valor if v not in Sector.values]
    if invalidos:
        raise ValidationError(
            "Sectores no permitidos: %(sectores)s.",
            code="sectores_invalidos",
            params={"sectores": ", ".join(str(v) for v in invalidos)},
        )
    if len(set(valor)) != len(valor):
        raise ValidationError("Hay sectores repetidos.", code="sectores_repetidos")
