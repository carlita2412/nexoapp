from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .models import (
    Asignacion,
    Catalogo,
    CentroSalud,
    Donacion,
    Envio,
    Necesidad,
    Organizacion,
)
from .serializers import (
    AsignacionSerializer,
    CandidatoDonacionSerializer,
    CatalogoSerializer,
    CentroSaludSerializer,
    DonacionSerializer,
    EnvioSerializer,
    NecesidadSerializer,
    OrganizacionSerializer,
    ClaimSerializer,
)
from .sync.matching import obtener_candidatos_para_necesidad
from .sync.arbitraje import ClaimError, reclamar_necesidad
@api_view(["GET"])
def salud(request):
    return Response(
        {
            "status": "ok",
            "servicio": "nexo",
            "version": "v1",
        }
    )


class OrganizacionViewSet(viewsets.ModelViewSet):
    queryset = Organizacion.objects.all().order_by("nombre")
    serializer_class = OrganizacionSerializer


class CatalogoViewSet(viewsets.ModelViewSet):
    queryset = Catalogo.objects.all().order_by("nombre")
    serializer_class = CatalogoSerializer


class CentroSaludViewSet(viewsets.ModelViewSet):
    queryset = CentroSalud.objects.all().order_by("nombre")
    serializer_class = CentroSaludSerializer


class NecesidadViewSet(viewsets.ModelViewSet):
    queryset = Necesidad.objects.all().order_by("-created_at")
    serializer_class = NecesidadSerializer

    @action(detail=True, methods=["get"], url_path="candidatos")
    def candidatos(self, request, pk=None):
        necesidad = self.get_object()
        resultados = obtener_candidatos_para_necesidad(necesidad)

        data = []

        for resultado in resultados:
            donacion = resultado.donacion

            data.append(
                {
                    "id": donacion.id,
                    "item": donacion.item.nombre,
                    "donante": donacion.donante.nombre,
                    "cantidad_disponible": donacion.cantidad,
                    "condicion": donacion.condicion,
                    "ubicacion_texto": donacion.ubicacion_texto,
                    "compatible": resultado.compatible,
                    "motivo": resultado.motivo,
                    "puntaje": resultado.puntaje,
                }
            )

        serializer = CandidatoDonacionSerializer(data, many=True)

        return Response(
            {
                "necesidad": str(necesidad.id),
                "item": necesidad.item.nombre,
                "centro": necesidad.centro.nombre,
                "cantidad_solicitada": necesidad.cantidad_solicitada,
                "cantidad_cubierta": necesidad.cantidad_cubierta,
                "cantidad_pendiente": necesidad.cantidad_solicitada
                - necesidad.cantidad_cubierta,
                "candidatos": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
    @action(detail=True, methods=["post"], url_path="claim")
    def claim(self, request, pk=None):
        necesidad = self.get_object()
        serializer = ClaimSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            asignacion = reclamar_necesidad(
                necesidad_id=necesidad.id,
                donacion_id=serializer.validated_data["donacion_id"],
                cantidad_asignada=serializer.validated_data["cantidad_asignada"],
                organizacion_responsable_id=serializer.validated_data[
                    "organizacion_responsable_id"
                ],
            )
        except ClaimError as exc:
            return Response(
                {
                    "estado": "rechazada",
                    "mensaje": str(exc),
                },
                status=400,
            )

        return Response(
            {
                "estado": asignacion.estado_claim,
                "mensaje": "Claim confirmado.",
                "asignacion": AsignacionSerializer(asignacion).data,
            },
            status=201,
        )

class DonacionViewSet(viewsets.ModelViewSet):
    queryset = Donacion.objects.all().order_by("-created_at")
    serializer_class = DonacionSerializer


class AsignacionViewSet(viewsets.ModelViewSet):
    queryset = Asignacion.objects.all().order_by("-created_at")
    serializer_class = AsignacionSerializer


class EnvioViewSet(viewsets.ModelViewSet):
    queryset = Envio.objects.all().order_by("-created_at")
    serializer_class = EnvioSerializer