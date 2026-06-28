from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.utils.dateparse import parse_datetime
from .auditoria import (
    ACCION_ADMINISTRAR_CATALOGO,
    ACCION_ADMINISTRAR_ORGANIZACION,
    ACCION_CONFIRMAR_ENTREGA,
    ACCION_CREAR_DONACION,
    ACCION_CREAR_NECESIDAD,
    ACCION_RECLAMAR_NECESIDAD,
    registrar_auditoria,
)
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


class AuditoriaCriticaMixin:
    """Registra acciones criticas sin repetir codigo en cada ViewSet."""

    entidad_auditoria = ""
    acciones_auditoria = {}

    def _registrar_auditoria(self, accion, objeto, operacion, extra=None):
        if not accion:
            return

        detalle = {
            "operacion": operacion,
            "endpoint": self.request.path,
            "metodo": self.request.method,
        }
        if extra:
            detalle.update(extra)

        registrar_auditoria(
            usuario=self.request.user,
            accion=accion,
            entidad=self.entidad_auditoria or objeto.__class__.__name__.lower(),
            entidad_id=getattr(objeto, "id", None),
            detalle=detalle,
        )

    def perform_create(self, serializer):
        objeto = serializer.save()
        self._registrar_auditoria(
            self.acciones_auditoria.get("create"),
            objeto,
            "create",
        )

    def perform_update(self, serializer):
        objeto = serializer.save()
        self._registrar_auditoria(
            self.acciones_auditoria.get("update"),
            objeto,
            "update",
        )

    def perform_destroy(self, instance):
        self._registrar_auditoria(
            self.acciones_auditoria.get("delete"),
            instance,
            "delete",
        )
        instance.delete()


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
    resultado = procesar_lote_sync(eventos, usuario=request.user)

    return Response(resultado, status=status.HTTP_200_OK)


class OrganizacionViewSet(AuditoriaCriticaMixin, viewsets.ModelViewSet):
    # Alta/baja de organizaciones de la alianza: solo admin.
    roles_escritura = SOLO_ADMIN
    entidad_auditoria = "organizacion"
    acciones_auditoria = {
        "create": ACCION_ADMINISTRAR_ORGANIZACION,
        "update": ACCION_ADMINISTRAR_ORGANIZACION,
        "delete": ACCION_ADMINISTRAR_ORGANIZACION,
    }
    queryset = Organizacion.objects.all().order_by("nombre")
    serializer_class = OrganizacionSerializer


class CatalogoViewSet(AuditoriaCriticaMixin, viewsets.ModelViewSet):
    # El catálogo es vocabulario crítico del matching: solo admin lo administra.
    roles_escritura = SOLO_ADMIN
    entidad_auditoria = "catalogo"
    acciones_auditoria = {
        "create": ACCION_ADMINISTRAR_CATALOGO,
        "update": ACCION_ADMINISTRAR_CATALOGO,
        "delete": ACCION_ADMINISTRAR_CATALOGO,
    }
    queryset = Catalogo.objects.all().order_by("nombre")
    serializer_class = CatalogoSerializer


class CentroSaludViewSet(viewsets.ModelViewSet):
    # Campo actualiza estado operativo del centro en terreno.
    roles_escritura = TODOS_OPERATIVOS
    queryset = CentroSalud.objects.all().order_by("nombre")
    serializer_class = CentroSaludSerializer


class NecesidadViewSet(AuditoriaCriticaMixin, viewsets.ModelViewSet):
    # Captura de necesidades: roles operativos. El claim tiene control adicional.
    roles_escritura = TODOS_OPERATIVOS
    entidad_auditoria = "necesidad"
    acciones_auditoria = {"create": ACCION_CREAR_NECESIDAD}
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

        registrar_auditoria(
            usuario=request.user,
            accion=ACCION_RECLAMAR_NECESIDAD,
            entidad="asignacion",
            entidad_id=asignacion.id,
            detalle={
                "endpoint": request.path,
                "metodo": request.method,
                "necesidad_id": str(necesidad.id),
                "donacion_id": str(asignacion.donacion_id),
                "cantidad_asignada": asignacion.cantidad_asignada,
                "organizacion_responsable_id": str(
                    asignacion.organizacion_responsable_id
                ),
                "estado_claim": asignacion.estado_claim,
                "idempotency_key": str(asignacion.idempotency_key)
                if asignacion.idempotency_key
                else None,
            },
        )

        return Response(
            {
                "estado": asignacion.estado_claim,
                "mensaje": "Claim confirmado.",
                "asignacion": AsignacionSerializer(asignacion).data,
            },
            status=201,
        )


class DonacionViewSet(AuditoriaCriticaMixin, viewsets.ModelViewSet):
    roles_escritura = TODOS_OPERATIVOS
    entidad_auditoria = "donacion"
    acciones_auditoria = {"create": ACCION_CREAR_DONACION}
    queryset = Donacion.objects.all().order_by("-created_at")
    serializer_class = DonacionSerializer


class AsignacionViewSet(viewsets.ModelViewSet):
    # La asignación nace del claim arbitrado; el CRUD manual queda en coordinación
    # para no saltarse el arbitraje (§5).
    permission_classes = [EsCoordinacionParaEscribir]
    queryset = Asignacion.objects.all().order_by("-created_at")
    serializer_class = AsignacionSerializer


class EnvioViewSet(AuditoriaCriticaMixin, viewsets.ModelViewSet):
    roles_escritura = TODOS_OPERATIVOS
    entidad_auditoria = "envio"
    acciones_auditoria = {
        "create": ACCION_CONFIRMAR_ENTREGA,
        "update": ACCION_CONFIRMAR_ENTREGA,
    }
    queryset = Envio.objects.all().order_by("-created_at")
    serializer_class = EnvioSerializer
