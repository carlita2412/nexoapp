from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.utils.dateparse import parse_datetime
from .permisos import (
    SOLO_ADMIN,
    SOLO_COORDINACION,
    TODOS_OPERATIVOS,
    EsCoordinacionParaEscribir,
    puede_escribir,
    puede_reclamar_necesidad,
)
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
    SyncPushSerializer,
)
from .sync.matching import obtener_candidatos_para_necesidad
from .sync.arbitraje import ClaimError, reclamar_necesidad
from .sync.procesador import obtener_deltas, procesar_lote_sync


@api_view(["GET"])
@permission_classes([AllowAny])
def salud(request):
    return Response(
        {
            "status": "ok",
            "servicio": "nexo",
            "version": "v1",
        }
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def sync(request):
    if request.method == "GET":
        # Pull (delta): cualquier usuario autenticado, incluido rol lectura.
        desde = request.query_params.get("desde")
        cursor = parse_datetime(desde) if desde else None
        data = obtener_deltas(desde=cursor)
        return Response(data)

    # Push (outbox): solo roles operativos (admin/coordinador/campo).
    if not puede_escribir(request.user, TODOS_OPERATIVOS):
        return Response(
            {"detail": "Tu rol no puede enviar eventos de sincronización."},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = SyncPushSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    eventos = serializer.validated_data["eventos"]
    resultado = procesar_lote_sync(eventos)

    return Response(resultado, status=status.HTTP_200_OK)


class OrganizacionViewSet(viewsets.ModelViewSet):
    # Alta/baja de organizaciones de la alianza: solo admin.
    roles_escritura = SOLO_ADMIN
    queryset = Organizacion.objects.all().order_by("nombre")
    serializer_class = OrganizacionSerializer


class CatalogoViewSet(viewsets.ModelViewSet):
    # El catálogo es vocabulario crítico del matching: solo admin lo administra.
    roles_escritura = SOLO_ADMIN
    queryset = Catalogo.objects.all().order_by("nombre")
    serializer_class = CatalogoSerializer


class CentroSaludViewSet(viewsets.ModelViewSet):
    # Campo actualiza estado operativo del centro en terreno.
    roles_escritura = TODOS_OPERATIVOS
    queryset = CentroSalud.objects.all().order_by("nombre")
    serializer_class = CentroSaludSerializer


class NecesidadViewSet(viewsets.ModelViewSet):
    # Captura de necesidades: roles operativos. El claim tiene control adicional.
    roles_escritura = TODOS_OPERATIVOS
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

        if not puede_reclamar_necesidad(
            request.user,
            serializer.validated_data["organizacion_responsable_id"],
        ):
            return Response(
                {
                    "detail": (
                        "Tu rol no puede reclamar esta necesidad para esa "
                        "organización."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            asignacion = reclamar_necesidad(
                necesidad_id=necesidad.id,
                donacion_id=serializer.validated_data["donacion_id"],
                cantidad_asignada=serializer.validated_data["cantidad_asignada"],
                organizacion_responsable_id=serializer.validated_data[
                    "organizacion_responsable_id"
                ],
                idempotency_key=serializer.validated_data.get("idempotency_key"),
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
    roles_escritura = TODOS_OPERATIVOS
    queryset = Donacion.objects.all().order_by("-created_at")
    serializer_class = DonacionSerializer


class AsignacionViewSet(viewsets.ModelViewSet):
    # La asignación nace del claim arbitrado; el CRUD manual queda en coordinación
    # para no saltarse el arbitraje (§5).
    permission_classes = [EsCoordinacionParaEscribir]
    queryset = Asignacion.objects.all().order_by("-created_at")
    serializer_class = AsignacionSerializer


class EnvioViewSet(viewsets.ModelViewSet):
    roles_escritura = TODOS_OPERATIVOS
    queryset = Envio.objects.all().order_by("-created_at")
    serializer_class = EnvioSerializer
