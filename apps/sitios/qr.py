"""Código QR de un punto de control: contenido y PNG con sitio, punto y sector."""

from io import BytesIO

import segno
from django.conf import settings
from django.urls import reverse
from PIL import Image, ImageDraw, ImageFont

# Barlow (OFL) trae los glifos acentuados que la fuente por defecto de Pillow no tiene.
RUTA_FUENTE = settings.BASE_DIR / "static/fonts/barlow-latin-600-normal.woff2"


def contenido_qr(punto):
    """URL pública que codifica el QR del punto."""
    return settings.SITE_URL + reverse("web:qr", args=[punto.qr_codigo])


def png_qr(punto):
    """Bytes de un PNG con el QR y debajo el sitio, el punto y su sector."""
    buffer = BytesIO()
    segno.make(contenido_qr(punto), error="m").save(
        buffer, kind="png", scale=10, border=4
    )
    buffer.seek(0)
    qr = Image.open(buffer).convert("RGB")
    lineas = [punto.sitio.nombre, punto.nombre]
    if punto.sector:
        lineas.append(punto.sector)
    lienzo = Image.new("RGB", (qr.width, qr.height + 18 + 36 * len(lineas)), "white")
    lienzo.paste(qr, (0, 0))
    dibujo = ImageDraw.Draw(lienzo)
    fuente = ImageFont.truetype(RUTA_FUENTE, 22)
    for fila, texto in enumerate(lineas):
        ancho = dibujo.textlength(texto, font=fuente)
        dibujo.text(
            (max((qr.width - ancho) / 2, 0), qr.height + 10 + fila * 36),
            texto,
            fill="black",
            font=fuente,
        )
    salida = BytesIO()
    lienzo.save(salida, format="PNG")
    return salida.getvalue()
