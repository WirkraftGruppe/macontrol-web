"""Imágenes de la demostración dibujadas con Pillow: plano esquemático y fotos."""

import random
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image, ImageDraw

COLUMNAS_PLANO = 4
ANCHO_PLANO, ALTO_PLANO = 960, 560
MARGEN = 30


def _celda(indice, total):
    """Fracciones (x0, y0, x1, y1) de la sala `indice` en una grilla de 4 columnas."""
    filas = -(-total // COLUMNAS_PLANO)
    fila, columna = divmod(indice, COLUMNAS_PLANO)
    ancho, alto = 1 / COLUMNAS_PLANO, 1 / filas
    return columna * ancho, fila * alto, (columna + 1) * ancho, (fila + 1) * alto


def posicion_en_plano(indice, total):
    """Centro de la sala `indice` como fracciones (x, y) entre 0 y 1."""
    x0, y0, x1, y1 = _celda(indice, total)
    return round((x0 + x1) / 2, 4), round((y0 + y1) / 2, 4)


def _archivo(imagen, formato, nombre):
    salida = BytesIO()
    imagen.save(salida, format=formato)
    return SimpleUploadedFile(nombre, salida.getvalue())


def plano_esquematico(nombres):
    """Plano de planta con una sala rotulada por cada nombre, en PNG."""
    imagen = Image.new("RGB", (ANCHO_PLANO, ALTO_PLANO), "#f4f1ea")
    dibujo = ImageDraw.Draw(imagen)
    util_x, util_y = ANCHO_PLANO - 2 * MARGEN, ALTO_PLANO - 2 * MARGEN
    for indice, nombre in enumerate(nombres):
        x0, y0, x1, y1 = _celda(indice, len(nombres))
        caja = [
            MARGEN + x0 * util_x,
            MARGEN + y0 * util_y,
            MARGEN + x1 * util_x,
            MARGEN + y1 * util_y,
        ]
        dibujo.rectangle(caja, fill="#e3e8ee", outline="#334155", width=4)
        dibujo.text((caja[0] + 10, caja[1] + 10), nombre, fill="#334155")
    dibujo.text((MARGEN, 8), "Plano esquemático (demostración)", fill="#334155")
    return _archivo(imagen, "PNG", "plano.png")


def foto_de_demostracion(semilla):
    """Foto JPEG genérica (formas sobre un fondo de color), distinta por semilla."""
    azar = random.Random(semilla)
    base = tuple(azar.randint(90, 170) for _ in range(3))
    imagen = Image.new("RGB", (640, 480), base)
    dibujo = ImageDraw.Draw(imagen)
    for _ in range(6):
        x, y = azar.randint(0, 520), azar.randint(0, 380)
        color = tuple(azar.randint(40, 220) for _ in range(3))
        caja = [x, y, x + azar.randint(40, 120), y + azar.randint(30, 100)]
        if azar.random() < 0.5:
            dibujo.ellipse(caja, fill=color)
        else:
            dibujo.rectangle(caja, fill=color)
    dibujo.text((16, 16), "Foto de demostración", fill="white")
    return _archivo(imagen, "JPEG", "foto.jpg")
