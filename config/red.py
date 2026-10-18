"""Datos de red de la petición."""

import ipaddress
import re

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

_NOMBRE_CABECERA = re.compile(r"HTTP_[A-Z0-9_]+")


def ip_del_cliente(request):
    """Devuelve la IP del cliente, por cabecera del borde o por `NUM_PROXIES`.

    Con `IP_CLIENTE_CABECERA` (nombre de `request.META`, `HTTP_[A-Z0-9_]+`) se
    toma la IP de esa cabecera, que el borde del hosting fija y sobrescribe; en
    Railway es `HTTP_X_REAL_IP`, porque Railway garantiza `X-Real-IP` pero no
    `X-Forwarded-For`. Tiene prioridad sobre `NUM_PROXIES` y `X-Forwarded-For`
    se ignora. Si la cabecera falta o no es una IP válida, es `REMOTE_ADDR`:
    nunca se devuelve un valor del cliente sin validar. Un nombre inválido
    lanza `ImproperlyConfigured`.

    Sin cabecera configurada: con `NUM_PROXIES == 0` es `REMOTE_ADDR` y se
    ignora `X-Forwarded-For`, que el cliente puede falsificar. Con N > 0 es la
    N-ésima IP desde el final de `X-Forwarded-For` (la que agregó el proxy más
    cercano a la aplicación); si hay menos de N entradas, `REMOTE_ADDR`. Es más
    seguro que el primer elemento de la lista, que controla el cliente.
    """
    remota = request.META.get("REMOTE_ADDR", "")
    cabecera = getattr(settings, "IP_CLIENTE_CABECERA", "")
    if cabecera:
        if not re.fullmatch(_NOMBRE_CABECERA, cabecera):
            raise ImproperlyConfigured(
                "IP_CLIENTE_CABECERA debe ser un nombre de request.META "
                "con la forma HTTP_[A-Z0-9_]+."
            )
        valor = str(request.META.get(cabecera, "")).strip()
        try:
            return str(ipaddress.ip_address(valor))
        except ValueError:
            return remota
    proxies = settings.NUM_PROXIES
    if proxies > 0:
        reenviadas = request.META.get("HTTP_X_FORWARDED_FOR", "")
        direcciones = [d.strip() for d in reenviadas.split(",") if d.strip()]
        if len(direcciones) >= proxies:
            return direcciones[-proxies]
    return remota
