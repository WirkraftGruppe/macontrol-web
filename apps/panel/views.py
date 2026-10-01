"""Vista provisoria del panel: texto fijo, sin datos."""

from django.http import HttpResponse


def inicio(request):
    return HttpResponse("Panel de gestión de MAControl S.A.")
