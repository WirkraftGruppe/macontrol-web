"""Vistas provisorias del sitio público: texto fijo, sin datos."""

from django.http import HttpResponse


def inicio(request):
    return HttpResponse("Sitio de MAControl S.A.")


def qr(request, codigo):
    """Aterrizaje de un QR en el navegador. No usa ni muestra el código."""
    return HttpResponse("Sitio de MAControl S.A. — use la app")
