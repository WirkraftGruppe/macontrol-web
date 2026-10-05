"""Código QR de un sitio: contenido y imagen PNG con el nombre debajo."""

from io import BytesIO

import segno
from django.conf import settings
from django.urls import reverse
from PIL import Image, ImageDraw, ImageFont


def contenido_qr(sitio):
    """URL pública que codifica el QR del sitio."""
    return settings.SITE_URL + reverse("web:qr", args=[sitio.qr_codigo])


def png_qr(sitio):
    """Devuelve los bytes de un PNG con el QR del sitio y su nombre debajo."""
    buffer = BytesIO()
    segno.make(contenido_qr(sitio), error="m").save(
        buffer, kind="png", scale=10, border=4
    )
    buffer.seek(0)
    qr = Image.open(buffer).convert("RGB")
    lienzo = Image.new("RGB", (qr.width, qr.height + 50), "white")
    lienzo.paste(qr, (0, 0))
    dibujo = ImageDraw.Draw(lienzo)
    fuente = ImageFont.load_default(size=22)
    texto = sitio.nombre
    ancho = dibujo.textlength(texto, font=fuente)
    dibujo.text(
        (max((qr.width - ancho) / 2, 0), qr.height + 10),
        texto,
        fill="black",
        font=fuente,
    )
    salida = BytesIO()
    lienzo.save(salida, format="PNG")
    return salida.getvalue()
