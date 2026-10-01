"""Vista provisoria de la API: texto fijo, sin datos."""

from django.http import HttpResponse


def raiz(request):
    return HttpResponse("API de MAControl S.A.")
