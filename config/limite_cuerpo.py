"""Tope al tamaño del cuerpo de las peticiones, antes de leerlo."""

from django.conf import settings
from django.http import HttpResponse

LIMITE_CUERPO_BYTES_POR_DEFECTO = 3 * 1024 * 1024


class LimiteCuerpoMiddleware:
    """Responde 413 si `CONTENT_LENGTH` supera `settings.LIMITE_CUERPO_BYTES`.

    Va después de `SecurityMiddleware` y antes de `CsrfViewMiddleware`, que es
    quien lee el cuerpo de un POST.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tope = getattr(settings, "LIMITE_CUERPO_BYTES", LIMITE_CUERPO_BYTES_POR_DEFECTO)
        try:
            largo = int(request.META.get("CONTENT_LENGTH") or 0)
        except ValueError:
            largo = 0
        if largo > tope:
            return HttpResponse(
                "El cuerpo de la petición es demasiado grande.",
                status=413,
                content_type="text/plain; charset=utf-8",
            )
        return self.get_response(request)
