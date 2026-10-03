"""Vistas transversales de la API: raíz y tokens JWT."""

from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed, Throttled
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.utils import get_md5_hash_password
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.limites import baldes_llenos, limpiar_usuario_ip, registrar_fallo
from apps.accounts.red import ip_del_cliente


class IpDelClienteMixin:
    """Identifica al cliente con `ip_del_cliente` y no con `X-Forwarded-For` crudo."""

    def get_ident(self, request):
        return ip_del_cliente(request)


class ThrottleToken(IpDelClienteMixin, AnonRateThrottle):
    """Limita los pedidos anónimos de obtener tokens, por IP."""

    scope = "token"


class ThrottleRenovacion(IpDelClienteMixin, AnonRateThrottle):
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
    """Obtiene el token; comparte con el panel los baldes de fallos por usuario."""

    throttle_classes = [ThrottleToken]

    def post(self, request, *args, **kwargs):
        usuario = (
            request.data.get("username", "") if hasattr(request.data, "get") else ""
        )
        if not isinstance(usuario, str):
            usuario = ""
        if baldes_llenos(request, usuario, solo_usuario=True):
            raise Throttled()
        try:
            respuesta = super().post(request, *args, **kwargs)
        except AuthenticationFailed:
            registrar_fallo(request, usuario, solo_usuario=True)
            raise
        limpiar_usuario_ip(request, usuario)
        return respuesta


class RenovarToken(TokenRefreshView):
    serializer_class = RenovacionSerializer
    throttle_classes = [ThrottleRenovacion]
