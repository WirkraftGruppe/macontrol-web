"""Mide si el sitio responde mientras hay descargas lentas del video.

Uso: medir_descargas.py --pagina URL --video URL [--descargas 4] [--kbps 100]
                        [--limite 2.0] [--cada 2]

Lanza N descargas simultáneas del video, cada una leyendo a lo sumo `kbps` KB/s.
Mientras alguna siga activa pide `--pagina` cada `--cada` segundos. Salida por stdout:
una línea `AAAA-MM-DDTHH:MM:SS pagina <código> <ms>` por pedido de página (código
`000` si falla la conexión), una línea `descarga <n> <recibidos>/<Content-Length>
<segundos>` por descarga y, al final, exactamente una línea `PASA ...` o `FALLA ...`.

Sale con 0 solo si toda descarga recibió exactamente `Content-Length` bytes con 200
o 206, hubo al menos un pedido de página y todos dieron 200 en menos de `--limite`
segundos. Un `Content-Length` ausente cuenta como falla.
"""

import argparse
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime

TIEMPO_MAXIMO_PEDIDO = 30.0
BLOQUES_POR_SEGUNDO = 10


class _SinRedirecciones(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


_abridor = urllib.request.build_opener(_SinRedirecciones)


def pedir_pagina(url):
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


def descargar(url, kbps, resultado):
    """Descarga `url` sin superar `kbps` KB/s y llena `resultado` con lo medido."""
    resultado.update(recibidos=0, largo=None, codigo=0, segundos=0.0)
    bytes_por_segundo = max(1, int(kbps * 1024))
    bloque = max(1, bytes_por_segundo // BLOQUES_POR_SEGUNDO)
    inicio = time.monotonic()
    try:
        with _abridor.open(url, timeout=TIEMPO_MAXIMO_PEDIDO) as respuesta:
            resultado["codigo"] = respuesta.status
            largo = respuesta.headers.get("Content-Length")
            resultado["largo"] = int(largo) if largo is not None else None
            while True:
                datos = respuesta.read(bloque)
                if not datos:
                    break
                resultado["recibidos"] += len(datos)
                # Espera lo necesario para no pasar de la velocidad pedida.
                adelanto = resultado["recibidos"] / bytes_por_segundo
                adelanto -= time.monotonic() - inicio
                if adelanto > 0:
                    time.sleep(adelanto)
    except urllib.error.HTTPError as error:
        resultado["codigo"] = error.code
    except (OSError, ValueError, urllib.error.URLError):
        pass
    resultado["segundos"] = time.monotonic() - inicio


def _descarga_completa(resultado):
    return (
        resultado["codigo"] in (200, 206)
        and resultado["largo"] is not None
        and resultado["recibidos"] == resultado["largo"]
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Mide la página mientras hay descargas lentas del video."
    )
    parser.add_argument("--pagina", required=True, help="URL de la página a pedir")
    parser.add_argument("--video", required=True, help="URL del video a descargar")
    parser.add_argument(
        "--descargas", type=int, default=4, help="descargas simultáneas"
    )
    parser.add_argument("--kbps", type=float, default=100.0, help="KB/s por descarga")
    parser.add_argument(
        "--limite", type=float, default=2.0, help="segundos máximos por página"
    )
    parser.add_argument(
        "--cada", type=float, default=2.0, help="segundos entre pedidos de página"
    )
    args = parser.parse_args(argv)

    resultados = [{} for _ in range(args.descargas)]
    hilos = [
        threading.Thread(target=descargar, args=(args.video, args.kbps, r), daemon=True)
        for r in resultados
    ]
    for hilo in hilos:
        hilo.start()

    paginas = 0
    lentas = 0
    while True:
        codigo, ms = pedir_pagina(args.pagina)
        marca = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        print(f"{marca} pagina {codigo:03d} {ms}", flush=True)
        paginas += 1
        if codigo != 200 or ms >= args.limite * 1000:
            lentas += 1
        pausa_hasta = time.monotonic() + args.cada
        while time.monotonic() < pausa_hasta and any(h.is_alive() for h in hilos):
            time.sleep(min(0.02, args.cada))
        if not any(h.is_alive() for h in hilos):
            break
    for hilo in hilos:
        hilo.join()

    incompletas = 0
    for numero, r in enumerate(resultados, start=1):
        largo = "-" if r["largo"] is None else r["largo"]
        print(f"descarga {numero} {r['recibidos']}/{largo} {r['segundos']:.1f}")
        if not _descarga_completa(r):
            incompletas += 1

    if incompletas or lentas or not paginas:
        print(
            f"FALLA {incompletas} descargas incompletas, {lentas} de {paginas} "
            f"pedidos de página fuera de 200 o sobre {args.limite} s"
        )
        return 1
    print(
        f"PASA {args.descargas} descargas completas, {paginas} pedidos de página sanos"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
