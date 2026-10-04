"""Serializers transversales de la API."""

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.limites import normalizar_usuario


class TokenNormalizadoSerializer(TokenObtainPairSerializer):
    """Normaliza el usuario igual que el panel antes de autenticar."""

    def validate(self, attrs):
        campo = self.username_field
        attrs[campo] = normalizar_usuario(attrs.get(campo))
        return super().validate(attrs)
