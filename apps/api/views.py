"""Vistas transversales de la API: raíz y tokens JWT."""

from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


class ThrottleAutenticacion(AnonRateThrottle):
    """Limita los intentos anónimos de obtener o renovar tokens."""

    scope = "autenticacion"


class RaizView(APIView):
    """Con los permisos por defecto: anónimo 401, autenticado ve su rol."""

    def get(self, request):
        return Response({"usuario": request.user.username, "rol": request.user.rol})


class ObtenerToken(TokenObtainPairView):
    throttle_classes = [ThrottleAutenticacion]


class RenovarToken(TokenRefreshView):
    throttle_classes = [ThrottleAutenticacion]
