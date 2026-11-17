"""Genera los iconos del sitio y la imagen para compartir (solo Pillow).

Uso, desde la raíz del repositorio:

    ./venv/Scripts/python.exe herramientas/generar_identidad.py [--salida <dir>]

Escribe en `<dir>` (por defecto `static/`): `favicon.ico` (16 y 32) y, en
`<dir>/img/`, `apple-touch-icon.png` (180), `icono-192.png`, `icono-512.png` y
`og-macontrol.png` (1200x630). Es idempotente: volver a correrlo reproduce los
mismos píxeles. El favicon replica `static/img/favicon.svg` (Adjunto B del plan).
"""

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
LOGO = RAIZ / "static" / "img" / "logo.png"
FUENTE = RAIZ / "static" / "fonts" / "barlow-condensed-latin-700-normal.woff2"

AMARILLO = "#ffc600"
FONDO = "#0f1417"
TEXTO = "#e8e6df"
ESLOGAN = "Manejo integral de plagas"

LADO_BASE = 512 * 8  # se dibuja a 8x del mayor tamaño y se reduce con LANCZOS
UNIDAD = LADO_BASE / 64  # píxeles por unidad del viewBox 0 0 64 64
RADIO_ESQUINA = 12.8  # 20 % del lado
GROSOR = 6
RADIO_ARCO = 4


def _arco(cx: float, cy: float, desde: int, hasta: int) -> list[tuple[float, float]]:
    """Puntos de un arco de radio 4 (ángulos en grados, eje y hacia abajo)."""
    pasos = 24
    puntos = []
    for i in range(pasos + 1):
        angulo = math.radians(desde + (hasta - desde) * i / pasos)
        puntos.append(
            (cx + RADIO_ARCO * math.cos(angulo), cy + RADIO_ARCO * math.sin(angulo))
        )
    return puntos


# Trazos del Adjunto B, en unidades del viewBox (los arcos "a4 4" aproximados).
TRAZOS = [
    # M: M9.5 44 V25 a4 4 0 0 1 4 -4 H24.5 a4 4 0 0 1 4 4 V44
    [(9.5, 44), *_arco(13.5, 25, 180, 270), *_arco(24.5, 25, 270, 360), (28.5, 44)],
    # M: M19 21 V44
    [(19, 21), (19, 44)],
    # C: M57.5 21 H43 a4 4 0 0 0 -4 4 V40 a4 4 0 0 0 4 4 H57.5
    [(57.5, 21), *_arco(43, 25, 270, 180), *_arco(43, 40, 180, 90), (57.5, 44)],
]


def _trazar(lapiz: ImageDraw.ImageDraw, puntos: list[tuple[float, float]]) -> None:
    """Trazo grueso: extremos rectos, uniones redondas, un cuadrilátero por tramo."""
    medio = GROSOR * UNIDAD / 2
    for (x0, y0), (x1, y1) in zip(puntos, puntos[1:]):
        largo = math.hypot(x1 - x0, y1 - y0)
        nx, ny = -(y1 - y0) / largo * medio, (x1 - x0) / largo * medio
        lapiz.polygon(
            [
                (x0 + nx, y0 + ny),
                (x1 + nx, y1 + ny),
                (x1 - nx, y1 - ny),
                (x0 - nx, y0 - ny),
            ],
            fill=FONDO,
        )
    for x, y in puntos[1:-1]:
        lapiz.ellipse((x - medio, y - medio, x + medio, y + medio), fill=FONDO)


def dibujar_favicon() -> Image.Image:
    """Dibuja el favicon "MC" a LADO_BASE de lado, con esquinas transparentes."""
    imagen = Image.new("RGBA", (LADO_BASE, LADO_BASE), (0, 0, 0, 0))
    lapiz = ImageDraw.Draw(imagen)
    lapiz.rounded_rectangle(
        (0, 0, LADO_BASE - 1, LADO_BASE - 1),
        radius=RADIO_ESQUINA * UNIDAD,
        fill=AMARILLO,
    )
    for trazo in TRAZOS:
        puntos = [(x * UNIDAD, y * UNIDAD) for x, y in trazo]
        _trazar(lapiz, puntos)
    return imagen


def dibujar_og() -> Image.Image:
    """Imagen 1200x630: el logo y el eslogan centrados sobre el fondo oscuro."""
    imagen = Image.new("RGB", (1200, 630), FONDO)
    logo = Image.open(LOGO).convert("RGBA")
    ancho_logo = 760
    logo = logo.resize(
        (ancho_logo, round(logo.height * ancho_logo / logo.width)), Image.LANCZOS
    )
    fuente = ImageFont.truetype(str(FUENTE), 64)
    izq, arriba, der, abajo = fuente.getbbox(ESLOGAN)
    separacion = 48
    alto_total = logo.height + separacion + (abajo - arriba)
    y_logo = (630 - alto_total) // 2
    imagen.paste(logo, ((1200 - ancho_logo) // 2, y_logo), logo)
    y_texto = y_logo + logo.height + separacion - arriba
    ImageDraw.Draw(imagen).text(
        ((1200 - (der - izq)) // 2 - izq, y_texto), ESLOGAN, font=fuente, fill=TEXTO
    )
    return imagen


def generar(salida: Path) -> list[Path]:
    """Escribe todos los archivos en `salida` y devuelve sus rutas."""
    img = salida / "img"
    img.mkdir(parents=True, exist_ok=True)
    base = dibujar_favicon()

    def reducir(lado: int) -> Image.Image:
        return base.resize((lado, lado), Image.LANCZOS)

    escritos = []
    for nombre, lado in (
        ("apple-touch-icon.png", 180),
        ("icono-192.png", 192),
        ("icono-512.png", 512),
    ):
        destino = img / nombre
        reducir(lado).save(destino, optimize=True)
        escritos.append(destino)
    ico = salida / "favicon.ico"
    reducir(256).save(ico, sizes=[(16, 16), (32, 32)])
    escritos.append(ico)
    og = img / "og-macontrol.png"
    dibujar_og().save(og, optimize=True)
    escritos.append(og)
    return escritos


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--salida", type=Path, default=RAIZ / "static", help="directorio de salida"
    )
    for ruta in generar(parser.parse_args().salida):
        print(ruta)


if __name__ == "__main__":
    main()
