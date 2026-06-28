from __future__ import annotations

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from coordinacion.kobo.mapeadores import MapeoKoboError
from coordinacion.kobo.servicio import TIPOS_KOBO, procesar_submission_kobo


def _webhook_autorizado(request) -> bool:
    token_esperado = getattr(settings, "KOBO_WEBHOOK_TOKEN", "")
    if not token_esperado:
        return True
    token_recibido = request.headers.get("X-Kobo-Token") or request.query_params.get("token")
    return token_recibido == token_esperado


@api_view(["POST"])
@permission_classes([AllowAny])
def webhook_kobo(request, tipo: str):
    if tipo not in TIPOS_KOBO:
        return Response(
            {"detail": f"Tipo KoBo no soportado: {tipo}"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not _webhook_autorizado(request):
        return Response(
            {"detail": "Token de webhook inválido."},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        resultado = procesar_submission_kobo(tipo, request.data)
    except MapeoKoboError as exc:
        return Response(
            {"estado": "conflicto", "mensaje": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    codigo = status.HTTP_200_OK if resultado.get("estado") == "duplicado" else status.HTTP_201_CREATED
    return Response(resultado, status=codigo)
