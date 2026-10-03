"""Límites de fallos de ingreso: tres baldes de ventana deslizante en la caché.

- por IP: `INTENTOS_FALLIDOS_POR_IP` fallos en `VENTANA_MINUTOS`;
- por (usuario, IP): `FALLOS_POR_USUARIO_E_IP` fallos en `VENTANA_MINUTOS`;
- por usuario, desde cualquier IP: `FALLOS_POR_USUARIO` fallos en
  `VENTANA_USUARIO_MINUTOS`.

Solo cuentan los fallos. Si algún balde está lleno se responde 429 sin evaluar
la contraseña, así el bloqueo no sirve de oráculo. Los valores se leen de los
settings en cada uso.
"""

import hashlib
import ipaddress
import time
import unicodedata

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse

from .red import ip_del_cliente

MENSAJE_BLOQUEO = (
    "Demasiados intentos fallidos. Espere unos minutos e intente de nuevo."
)


def normalizar_usuario(texto):
    """Normaliza un nombre de usuario: NFKC, sin espacios en los extremos, casefold.

    Los usuarios ya guardados no se migran: uno guardado sin normalizar deja de
    poder ingresar hasta que se lo renombre.
    """
    return unicodedata.normalize("NFKC", texto or "").strip().casefold()


def _hash(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _grupo_de_ip(ip):
    """Agrupa las direcciones IPv6 por /64; una IP inválida se usa tal cual."""
    ip = (ip or "").strip()
    try:
        direccion = ipaddress.ip_address(ip)
    except ValueError:
        return ip.casefold()
    if direccion.version == 6:
        return str(ipaddress.ip_network(f"{ip}/64", strict=False))
    return str(direccion)


def _baldes(request, usuario):
    """Lista de (clave de caché, máximo de fallos, ventana en segundos)."""
    ip = _hash(_grupo_de_ip(ip_del_cliente(request)))
    nombre = _hash(normalizar_usuario(usuario))
    ventana = settings.VENTANA_MINUTOS * 60
    return [
        (f"ingreso:ip:{ip}", settings.INTENTOS_FALLIDOS_POR_IP, ventana),
        (
            f"ingreso:usuario-ip:{nombre}:{ip}",
            settings.FALLOS_POR_USUARIO_E_IP,
            ventana,
        ),
        (
            f"ingreso:usuario:{nombre}",
            settings.FALLOS_POR_USUARIO,
            settings.VENTANA_USUARIO_MINUTOS * 60,
        ),
    ]


def _fallos_vigentes(clave, ventana, ahora):
    return [t for t in cache.get(clave, []) if t > ahora - ventana]


def baldes_llenos(request, usuario, solo_usuario=False):
    """True si algún balde alcanzó su máximo; `solo_usuario` omite el balde por IP."""
    ahora = time.time()
    baldes = (
        _baldes(request, usuario)[1:] if solo_usuario else _baldes(request, usuario)
    )
    return any(
        len(_fallos_vigentes(clave, ventana, ahora)) >= maximo
        for clave, maximo, ventana in baldes
    )


def registrar_fallo(request, usuario, solo_usuario=False):
    """Anota un fallo ahora en los baldes; `solo_usuario` omite el balde por IP."""
    ahora = time.time()
    baldes = (
        _baldes(request, usuario)[1:] if solo_usuario else _baldes(request, usuario)
    )
    for clave, _maximo, ventana in baldes:
        fallos = _fallos_vigentes(clave, ventana, ahora)
        fallos.append(ahora)
        cache.set(clave, fallos, ventana)


def limpiar_usuario_ip(request, usuario):
    """Borra solo el balde (usuario, IP) tras un ingreso exitoso."""
    cache.delete(_baldes(request, usuario)[1][0])


class LimiteIngresoMixin:
    """Mixin para `LoginView`: aplica los tres baldes de fallos."""

    def _usuario_enviado(self):
        return normalizar_usuario(self.request.POST.get("username", ""))

    def post(self, request, *args, **kwargs):
        if baldes_llenos(request, self._usuario_enviado()):
            return HttpResponse(
                MENSAJE_BLOQUEO, status=429, content_type="text/plain; charset=utf-8"
            )
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        registrar_fallo(self.request, self._usuario_enviado())
        return super().form_invalid(form)

    def form_valid(self, form):
        limpiar_usuario_ip(self.request, self._usuario_enviado())
        return super().form_valid(form)
