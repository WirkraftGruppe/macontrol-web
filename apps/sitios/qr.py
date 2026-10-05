"""Código QR de un punto de control: contenido y PNG con sitio y punto debajo."""

from io import BytesIO

import segno
from django.conf import settings
from django.urls import reverse
from PIL import Image, ImageDraw, ImageFont


def contenido_qr(punto):
    """URL pública que codifica el QR del punto."""
    return settings.SITE_URL + reverse("web:qr", args=[punto.qr_codigo])


def png_qr(punto):
    """Devuelve los bytes de un PNG con el QR y debajo el sitio y el punto."""
    buffer = BytesIO()
    segno.make(contenido_qr(punto), error="m").save(
        buffer, kind="png", scale=10, border=4
    )
    buffer.seek(0)
    qr = Image.open(buffer).convert("RGB")
    lienzo = Image.new("RGB", (qr.width, qr.height + 90), "white")
    lienzo.paste(qr, (0, 0))
    dibujo = ImageDraw.Draw(lienzo)
    fuente = ImageFont.load_default(size=22)
    for fila, texto in enumerate((punto.sitio.nombre, punto.nombre)):
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
