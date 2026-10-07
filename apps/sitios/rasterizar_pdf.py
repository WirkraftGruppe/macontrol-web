"""Rasteriza la primera página de un PDF en un proceso aparte.

Se ejecuta como ``python -m apps.sitios.rasterizar_pdf <lado_maximo>``: lee el PDF
por stdin y escribe el PNG por stdout. pdfium no se puede interrumpir desde Python,
por eso el proceso web lo lanza como subproceso con un tiempo máximo. No importa
Django: solo pypdfium2 y PIL. Los errores salen por código de salida, sin texto.
"""

import sys
from io import BytesIO

import pypdfium2

SIN_PAGINAS = 3
SIN_TAMANO = 4
ILEGIBLE = 5
LIMITE_MEMORIA = 2 * 1024**3


def _limitar_memoria():
    """Tope de memoria del proceso; solo donde existe ``resource`` (no en Windows)."""
    try:
        import resource
    except ImportError:
        return
    try:
        resource.setrlimit(resource.RLIMIT_AS, (LIMITE_MEMORIA, LIMITE_MEMORIA))
    except (ValueError, OSError):
        pass


def rasterizar(datos, lado_maximo):
    """Devuelve el PNG de la página 0 con el lado mayor en ``lado_maximo`` px.

    Devuelve un entero (código de error) si el PDF no tiene páginas o tamaño, o si
    no se puede leer (corrupto o protegido con contraseña).
    """
    try:
        documento = pypdfium2.PdfDocument(datos)
        try:
            if len(documento) == 0:
                return SIN_PAGINAS
            pagina = documento[0]
            ancho, alto = pagina.get_size()
            if min(ancho, alto) <= 0:
                return SIN_TAMANO
            escala = lado_maximo / max(ancho, alto)
            imagen = pagina.render(scale=escala).to_pil().convert("RGB")
        finally:
            documento.close()
    except pypdfium2.PdfiumError:
        return ILEGIBLE
    salida = BytesIO()
    imagen.save(salida, format="PNG")
    return salida.getvalue()


def main():
    _limitar_memoria()
    resultado = rasterizar(sys.stdin.buffer.read(), int(sys.argv[1]))
    if isinstance(resultado, int):
        return resultado
    sys.stdout.buffer.write(resultado)
    return 0


if __name__ == "__main__":
    sys.exit(main())
