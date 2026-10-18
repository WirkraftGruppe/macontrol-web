"""Orden fijo de las directivas de la cabecera Content-Security-Policy."""

from csp.middleware import CSPMiddleware
from django.conf import settings

_CABECERAS = (
    ("Content-Security-Policy", "CONTENT_SECURITY_POLICY"),
    ("Content-Security-Policy-Report-Only", "CONTENT_SECURITY_POLICY_REPORT_ONLY"),
)


def reordenar_politica(politica, orden):
    """Devuelve `politica` con sus directivas según `orden` (nombres de directiva).

    Las directivas que no figuran en `orden` van al final, en el orden en que
    llegaron. No cambia valores ni agrega o quita directivas.
    """
    directivas = [d.strip() for d in politica.split(";") if d.strip()]
    posicion = {nombre: i for i, nombre in enumerate(orden)}
    # sorted es estable: las desconocidas conservan su orden relativo al final.
    ordenadas = sorted(
        directivas,
        key=lambda d: posicion.get(d.split(None, 1)[0], len(posicion)),
    )
    return "; ".join(ordenadas)


class CSPMiddlewareOrdenado(CSPMiddleware):
    """`CSPMiddleware` con las directivas en el orden de los settings.

    django-csp 4.0 arma la política con `set(chain(...))` (`csp/utils.py`), así
    que el orden de las directivas depende de `PYTHONHASHSEED` y cambia en cada
    arranque. El middleware base llama a la función `build_policy` del módulo,
    no a un método, por lo que no se puede sobrescribir: se reordena la
    cabecera ya armada según las claves de `CONTENT_SECURITY_POLICY["DIRECTIVES"]`
    (y de `CONTENT_SECURITY_POLICY_REPORT_ONLY`). El nonce y los valores no se
    tocan.
    """

    def process_response(self, request, response):
        response = super().process_response(request, response)
        for cabecera, nombre_setting in _CABECERAS:
            if cabecera in response:
                config = getattr(settings, nombre_setting, None) or {}
                orden = list(config.get("DIRECTIVES") or {})
                response[cabecera] = reordenar_politica(response[cabecera], orden)
        return response
