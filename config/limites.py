"""Límites de intentos de ingreso: tres baldes con contador por ventana en la base.

- por IP: `INTENTOS_FALLIDOS_POR_IP` fallos en `VENTANA_MINUTOS`;
- por (usuario, IP): `FALLOS_POR_USUARIO_E_IP` fallos en `VENTANA_MINUTOS`;
- por usuario, desde cualquier IP: `FALLOS_POR_USUARIO` fallos en
  `VENTANA_USUARIO_MINUTOS`.

Cada balde es una fila de `ContadorIngreso` por ventana fija. Cada POST reserva su
intento antes de evaluar la contraseña: suma 1 con un `UPDATE ... SET cuenta =
cuenta + 1` (atómico en la base, también con peticiones simultáneas), en orden (IP,
usuario e IP, usuario). Si un balde queda por encima de su máximo, devuelve lo
reservado en esa llamada, no toca los siguientes y responde 429 sin evaluar la
contraseña, así el bloqueo no sirve de oráculo y no cuenta como intento. Un ingreso correcto borra el balde (usuario, IP) y
devuelve la reserva de los baldes por IP y por usuario, de modo que solo cuentan los
fallos. Las filas vencidas se borran al reservar. Los valores se leen de los
settings en cada uso.
"""

import ipaddress
import time
import unicodedata
from datetime import UTC, datetime

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F
from django.http import HttpResponse
from django.utils.crypto import salted_hmac

from apps.web.models import ContadorIngreso
from config.red import ip_del_cliente

MENSAJE_BLOQUEO = (
    "Demasiados intentos fallidos. Espere unos minutos e intente de nuevo."
)


def normalizar_usuario(texto):
    """Normaliza un nombre de usuario: NFKC, sin espacios en los extremos, casefold.

    Esta función solo arma las claves de los límites: no toca la base ni el login.
    `auth.User` guarda el nombre tal cual lo escribió quien lo creó; la autenticación
    sigue comparando el nombre original, y las variantes de escritura comparten cupo.
    """
    return unicodedata.normalize("NFKC", texto or "").strip().casefold()


def _hash(texto):
    return salted_hmac("config.limites", texto).hexdigest()


def _grupo_de_ip(ip):
    """Agrupa las IPv6 por /64 y desmapea las IPv4 mapeadas; inválida: tal cual."""
    ip = (ip or "").strip()
    try:
        direccion = ipaddress.ip_address(ip)
    except ValueError:
        return ip.casefold()
    if direccion.version == 6:
        if direccion.ipv4_mapped is not None:
            return str(direccion.ipv4_mapped)
        return str(ipaddress.ip_network(f"{ip}/64", strict=False))
    return str(direccion)


def _baldes(request, usuario):
    """Lista de (clave base del balde, máximo de fallos, ventana en segundos)."""
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


def _clave_de_ventana(clave, ventana, ahora):
    return f"{clave}:{int(ahora // ventana)}"


def _vence_de_ventana(ventana, ahora):
    """Instante en que cierra la ventana fija en curso."""
    return datetime.fromtimestamp((int(ahora // ventana) + 1) * ventana, UTC)


def _sumar_reserva(clave, ventana, ahora):
    """Suma 1 al balde de la ventana en curso y devuelve su cuenta resultante."""
    identificador = _clave_de_ventana(clave, ventana, ahora)
    vence = _vence_de_ventana(ventana, ahora)
    for _ in range(3):
        try:
            ContadorIngreso.objects.get_or_create(
                clave=identificador, defaults={"cuenta": 0, "vence": vence}
            )
        except IntegrityError:
            # Otra petición creó la fila a la vez: se reintenta con `get`.
            continue
        # El UPDATE toma el bloqueo de la fila hasta el commit: la lectura siguiente
        # ve exactamente la cuenta que dejó esta reserva.
        with transaction.atomic():
            filas = ContadorIngreso.objects.filter(clave=identificador).update(
                cuenta=F("cuenta") + 1
            )
            if filas:
                return ContadorIngreso.objects.values_list("cuenta", flat=True).get(
                    clave=identificador
                )
        # La fila la borró la limpieza de otra petición: se vuelve a crear.
    return 1


def reservar_intento(request, usuario, solo_usuario=False):
    """Reserva un intento en los baldes; True si ninguno supera su máximo.

    `solo_usuario` omite el balde por IP. La reserva se hace antes de evaluar la
    contraseña; un ingreso correcto la devuelve con `devolver_reserva`.
    """
    ahora = time.time()
    ContadorIngreso.objects.filter(
        vence__lt=datetime.fromtimestamp(ahora, UTC)
    ).delete()
    baldes = (
        _baldes(request, usuario)[1:] if solo_usuario else _baldes(request, usuario)
    )
    # El instante queda en el request: la devolución resta en la misma ventana.
    request._ahora_limites = ahora
    # Se reserva en orden y se corta en el primer balde lleno: se devuelve lo
    # reservado en esta llamada y no se tocan los siguientes, así cuentan solo los
    # intentos que se evalúan y una IP bloqueada no crea filas de usuario.
    reservados = []
    for clave, maximo, ventana in baldes:
        reservados.append((clave, ventana))
        if _sumar_reserva(clave, ventana, ahora) > maximo:
            for clave_r, ventana_r in reservados:
                _restar_reserva(clave_r, ventana_r, ahora)
            return False
    return True


def _restar_reserva(clave, ventana, ahora):
    """Resta 1 al balde de la ventana indicada, sin bajar de 0."""
    ContadorIngreso.objects.filter(
        clave=_clave_de_ventana(clave, ventana, ahora), cuenta__gt=0
    ).update(cuenta=F("cuenta") - 1)


def devolver_reserva(request, usuario):
    """Tras un ingreso correcto: borra el balde (usuario, IP) y libera los otros dos."""
    ahora = getattr(request, "_ahora_limites", None) or time.time()
    baldes = _baldes(request, usuario)
    clave, _maximo, ventana = baldes[1]
    ContadorIngreso.objects.filter(
        clave=_clave_de_ventana(clave, ventana, ahora)
    ).delete()
    for clave, _maximo, ventana in (baldes[0], baldes[2]):
        _restar_reserva(clave, ventana, ahora)


class LimiteIngresoMixin:
    """Mixin para `LoginView`: reserva el intento antes de evaluar la contraseña."""

    def _usuario_enviado(self):
        return normalizar_usuario(self.request.POST.get("username", ""))

    def post(self, request, *args, **kwargs):
        if not reservar_intento(request, self._usuario_enviado()):
            return HttpResponse(
                MENSAJE_BLOQUEO, status=429, content_type="text/plain; charset=utf-8"
            )
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        devolver_reserva(self.request, self._usuario_enviado())
        return super().form_valid(form)
