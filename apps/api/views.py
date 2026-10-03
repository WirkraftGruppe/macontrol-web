"""Vistas transversales de la API: raíz y tokens JWT."""

from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.utils import get_md5_hash_password
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


class ThrottleAutenticacion(AnonRateThrottle):
    """Limita los intentos anónimos de obtener o renovar tokens."""

    scope = "autenticacion"


class ThrottleRenovacion(AnonRateThrottle):
    """Cupo propio para renovar tokens, aparte del de obtenerlos."""

    scope = "renovacion"
    rate = "30/min"


class RenovacionSerializer(TokenRefreshSerializer):
    """Rechaza renovar si el usuario no existe o cambió su contraseña."""

    def validate(self, attrs):
        refresh = self.token_class(attrs["refresh"])
        usuario = (
            get_user_model()
            .objects.filter(
                **{
                    api_settings.USER_ID_FIELD: refresh.payload.get(
                        api_settings.USER_ID_CLAIM
                    )
                }
            )
            .first()
        )
        reclamo = refresh.payload.get(api_settings.REVOKE_TOKEN_CLAIM)
        if usuario is None or reclamo != get_md5_hash_password(usuario.password):
            raise AuthenticationFailed(
                self.error_messages["no_active_account"], "no_active_account"
            )
        return super().validate(attrs)


class RaizView(APIView):
    """Con los permisos por defecto: anónimo 401, autenticado ve su rol."""

    def get(self, request):
        return Response({"usuario": request.user.username, "rol": request.user.rol})


class ObtenerToken(TokenObtainPairView):
    throttle_classes = [ThrottleAutenticacion]


class RenovarToken(TokenRefreshView):
    serializer_class = RenovacionSerializer
    throttle_classes = [ThrottleRenovacion]
