"""Autenticación por token para clientes de campo (PWA offline)."""
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


class LoginToken(ObtainAuthToken):
    """
    POST /api/v1/auth/token/  {"username": ..., "password": ...}

    Devuelve el token y el contexto mínimo de rol/organización que la PWA
    necesita para pintar la UI por rol sin volver a consultar.
    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        usuario = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=usuario)

        return Response(
            {
                "token": token.key,
                "usuario": usuario.username,
                "rol": usuario.rol,
                "organizacion": str(usuario.organizacion_id)
                if usuario.organizacion_id
                else None,
            }
        )
