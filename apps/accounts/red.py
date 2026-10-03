"""Datos de red de la petición."""

from django.conf import settings


def ip_del_cliente(request):
    """Devuelve la IP del cliente según la cantidad de proxies de confianza.

    Con `NUM_PROXIES == 0` es `REMOTE_ADDR` y se ignora `X-Forwarded-For`, que
    el cliente puede falsificar. Con N > 0 es la N-ésima IP desde el final de
    `X-Forwarded-For` (la que agregó el proxy más cercano a la aplicación);
    si hay menos de N entradas, `REMOTE_ADDR`. Es más seguro que el primer
    elemento de la lista, que usa DRF y que controla el cliente.
    """
    remota = request.META.get("REMOTE_ADDR", "")
    proxies = settings.NUM_PROXIES
    if proxies > 0:
        reenviadas = request.META.get("HTTP_X_FORWARDED_FOR", "")
        direcciones = [d.strip() for d in reenviadas.split(",") if d.strip()]
        if len(direcciones) >= proxies:
            return direcciones[-proxies]
    return remota
