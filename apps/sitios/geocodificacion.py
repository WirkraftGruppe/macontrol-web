"""Búsqueda de direcciones en Nominatim para ayudar a cargar coordenadas.

Solo se envía a Nominatim el texto de dirección que escribe el administrador en el
buscador; nunca nombres de clientes, de sitios ni de contactos.
"""

import hashlib
import http.client
import json
import logging
import math
import time
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

URL_NOMINATIM = "https://nominatim.openstreetmap.org/search"
USER_AGENT = f"MAControl/1.0 (+{settings.SITE_URL}; administracion@macontrol.com.ar)"
TIMEOUT_SEGUNDOS = 5
LIMITE_TOTAL_SEGUNDOS = 5
MAX_BYTES = 1_000_000
TAMANO_BLOQUE = 16_384
DURACION_CACHE = 24 * 60 * 60
MAX_LARGO_TEXTO = 200
MAX_CANDIDATOS = 5
CLAVE_TURNO = "sitios:geocodificacion:turno"
MENSAJE_CARGA_MANUAL = (
    "No se pudo consultar la ubicación; cárguela a mano en el mapa o en los campos."
)


class GeocodificacionError(Exception):
    """La consulta no se pudo hacer o no devolvió una respuesta utilizable."""


class TextoInvalido(ValueError):
    """El texto de búsqueda está vacío o es demasiado largo."""


class _SinRedirecciones(urllib.request.HTTPRedirectHandler):
    """No sigue redirecciones: el host de la consulta es siempre el fijo."""

    def redirect_request(self, *args, **kwargs):
        return None


def _abrir(solicitud):
    """Abre la solicitud sin seguir redirecciones y devuelve los bytes.

    Además del timeout por socket hay una fecha límite total: el cuerpo se lee con
    ``read1`` (una sola lectura de socket por vuelta) y la fecha se comprueba entre
    lecturas. Peor caso real: ``LIMITE_TOTAL_SEGUNDOS + TIMEOUT_SEGUNDOS`` con el cuerpo
    goteado; las cabeceras goteadas solo las acota el timeout por socket de ``open``.
    """
    limite = time.monotonic() + LIMITE_TOTAL_SEGUNDOS
    abridor = urllib.request.build_opener(_SinRedirecciones)
    partes = []
    leidos = 0
    with abridor.open(solicitud, timeout=TIMEOUT_SEGUNDOS) as respuesta:
        while leidos < MAX_BYTES:
            if time.monotonic() > limite:
                raise TimeoutError("se superó el tiempo total de la consulta")
            bloque = respuesta.read1(min(TAMANO_BLOQUE, MAX_BYTES - leidos))
            if not bloque:
                break
            partes.append(bloque)
            leidos += len(bloque)
    return b"".join(partes)


def normalizar(texto):
    """Minúsculas y espacios colapsados; valida que no esté vacío ni sea largo."""
    texto = " ".join((texto or "").split())
    if not texto or len(texto) > MAX_LARGO_TEXTO:
        raise TextoInvalido(texto)
    return texto.casefold()


def _coordenada(valor, limite):
    numero = float(valor)
    if not math.isfinite(numero) or abs(numero) > limite:
        raise ValueError(valor)
    return numero


def _candidatos(datos):
    resultado = []
    if not isinstance(datos, list):
        raise GeocodificacionError("respuesta inesperada")
    for item in datos:
        try:
            resultado.append(
                {
                    "nombre": str(item["display_name"])[:300],
                    "lat": _coordenada(item["lat"], 90),
                    "lng": _coordenada(item["lon"], 180),
                }
            )
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if len(resultado) == MAX_CANDIDATOS:
            break
    return resultado


def buscar(texto):
    """Hasta 5 candidatos ``{nombre, lat, lng}`` para el texto de dirección.

    Lanza ``TextoInvalido`` si el texto no sirve y ``GeocodificacionError`` si no se
    pudo consultar (sin red, error, o más de una consulta por segundo).
    """
    normalizado = normalizar(texto)
    clave = "sitios:geocodificacion:" + hashlib.sha256(normalizado.encode()).hexdigest()
    guardado = cache.get(clave)
    if guardado is not None:
        return guardado
    if not cache.add(CLAVE_TURNO, 1, 1):
        raise GeocodificacionError("límite de una consulta por segundo")
    parametros = urllib.parse.urlencode(
        {"q": normalizado, "format": "jsonv2", "limit": MAX_CANDIDATOS}
    )
    solicitud = urllib.request.Request(
        f"{URL_NOMINATIM}?{parametros}",
        headers={"User-Agent": USER_AGENT, "Accept-Language": "es"},
    )
    try:
        candidatos = _candidatos(json.loads(_abrir(solicitud)))
    except (
        urllib.error.URLError,
        OSError,
        ValueError,
        RecursionError,
        OverflowError,
        http.client.HTTPException,
    ) as error:
        logger.warning("Falló la consulta a Nominatim: %s", type(error).__name__)
        raise GeocodificacionError(str(error)) from error
    cache.set(clave, candidatos, DURACION_CACHE)
    return candidatos
