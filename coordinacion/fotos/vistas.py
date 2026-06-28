"""API de fotos de entrega: subida multipart en cola + descarga/metadatos."""
from django.conf import settings
from rest_framework import mixins, status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from coordinacion.models import Foto
from coordinacion.permisos import TODOS_OPERATIVOS
from coordinacion.serializers import FotoSerializer, FotoSubidaSerializer

from .tareas import encolar_procesamiento


class FotoViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    POST /api/v1/fotos/   (multipart: idempotency_key, envio, imagen)
        -> 202 Accepted, encola compresión. Idempotente por idempotency_key.
    GET  /api/v1/fotos/<id>/  -> metadatos + url (cualquier autenticado).
    """

    queryset = Foto.objects.all().order_by("-created_at")
    serializer_class = FotoSerializer
    parser_classes = [MultiPartParser, FormParser]
    roles_escritura = TODOS_OPERATIVOS  # solo roles operativos suben

    def create(self, request, *args, **kwargs):
        entrada = FotoSubidaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data

        # Rechazo defensivo de subidas enormes (§2 presupuesto de datos).
        imagen = datos["imagen"]
        maximo = getattr(settings, "FOTO_MAX_SUBIDA_BYTES", 5 * 1024 * 1024)
        if imagen.size > maximo:
            return Response(
                {
                    "detail": (
                        f"La imagen excede el máximo permitido "
                        f"({maximo} bytes). Comprime en el cliente antes de subir."
                    )
                },
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        # Idempotencia (§4): un reintento con la misma key devuelve la misma foto.
        existente = Foto.objects.filter(
            idempotency_key=datos["idempotency_key"]
        ).first()
        if existente is not None:
            return Response(
                self.get_serializer(existente).data,
                status=status.HTTP_200_OK,
            )

        foto = Foto.objects.create(
            idempotency_key=datos["idempotency_key"],
            envio=datos["envio"],
            original=imagen,
            estado=Foto.Estado.RECIBIDA,
        )

        encolar_procesamiento(foto.id)

        return Response(
            self.get_serializer(foto).data,
            status=status.HTTP_202_ACCEPTED,
        )
