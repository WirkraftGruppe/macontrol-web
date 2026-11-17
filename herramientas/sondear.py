"""Sondea una URL cada N segundos y registra una línea por sondeo.

Uso: sondear.py URL [--cada 5] [--durante 600]

Cada línea de stdout tiene el formato `AAAA-MM-DDTHH:MM:SS <código> <ms>` (hora local).
No sigue redirecciones: un 3xx se registra con su código. Un error de conexión o un
tiempo agotado se registra con el código `000`. Los resúmenes salen por stderr para
que stdout se pueda validar con grep. Sale con 0 si hubo al menos un sondeo y todos
dieron 200; si no, con 1.
"""

import argparse
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

TIEMPO_MAXIMO_PEDIDO = 10.0


class _SinRedirecciones(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


_abridor = urllib.request.build_opener(_SinRedirecciones)


def sondear_una_vez(url):
    """Hace un GET y devuelve `(código, ms)`; código 0 si falla la conexión."""
    inicio = time.monotonic()
    try:
        with _abridor.open(url, timeout=TIEMPO_MAXIMO_PEDIDO) as respuesta:
            respuesta.read()
            codigo = respuesta.status
    except urllib.error.HTTPError as error:
        codigo = error.code
    except (urllib.error.URLError, OSError, ValueError):
        codigo = 0
    return codigo, int((time.monotonic() - inicio) * 1000)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Sondea una URL cada N segundos.")
    parser.add_argument("url")
    parser.add_argument(
        "--cada", type=float, default=5.0, help="segundos entre sondeos"
    )
    parser.add_argument(
        "--durante", type=float, default=600.0, help="duración total en segundos"
    )
    args = parser.parse_args(argv)

    fin = time.monotonic() + args.durante
    total = 0
    fallidos = 0
    while True:
        codigo, ms = sondear_una_vez(args.url)
        marca = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        print(f"{marca} {codigo:03d} {ms}", flush=True)
        total += 1
        if codigo != 200:
            fallidos += 1
        if time.monotonic() + args.cada >= fin:
            break
        time.sleep(args.cada)

    print(f"{total} sondeos, {fallidos} distintos de 200", file=sys.stderr)
    return 0 if total and not fallidos else 1


if __name__ == "__main__":
    sys.exit(main())
