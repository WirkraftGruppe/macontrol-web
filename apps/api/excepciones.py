"""Manejador de excepciones: todo error sale como `{"detalle", "campos"}`."""

import logging

from django.core.exceptions import ValidationError as ErrorDeDjango
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)

DETALLE_VALIDACION = "Hay datos inválidos."
DETALLE_INTERNO = "Error interno del servidor."


def _como_lista(valor):
    if isinstance(valor, (list, tuple)):
        return [str(item) for item in valor]
    return [str(valor)]


def manejar_excepcion(exc, contexto):
    """Respuesta uniforme; las excepciones no previstas no exponen su texto."""
    if isinstance(exc, ErrorDeDjango):
        exc = ValidationError(exc.messages)
    respuesta = exception_handler(exc, contexto)
    if respuesta is None:
        logger.exception("Excepción no controlada en la API", exc_info=exc)
        return Response(
            {"detalle": DETALLE_INTERNO, "campos": {}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    campos = {}
    if isinstance(exc, ValidationError):
        if isinstance(respuesta.data, dict):
            campos = {str(k): _como_lista(v) for k, v in respuesta.data.items()}
            detalle = DETALLE_VALIDACION
        else:
            detalle = " ".join(_como_lista(respuesta.data))
    elif isinstance(exc, APIException):
        detalle = str(exc.detail)
    else:
        detalle = str(respuesta.data.get("detail", ""))
    respuesta.data = {"detalle": detalle, "campos": campos}
    return respuesta
