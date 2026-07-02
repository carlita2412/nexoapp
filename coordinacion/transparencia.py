from __future__ import annotations

from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Avg, Count, ExpressionWrapper, F, fields
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .geo import point_a_dict
from .models import Asignacion, Donacion, Envio, Necesidad, Organizacion


PIPELINE_DONACION = (
    Donacion.Estado.REGISTRADA,
    Donacion.Estado.ASIGNADA,
    Donacion.Estado.EN_TRANSITO,
    Donacion.Estado.ENTREGADA,
    Donacion.Estado.EN_USO,
)

ESTADOS_PUBLICABLES = set(PIPELINE_DONACION)


def _redondear_horas(delta: timedelta | None) -> float | None:
    if not delta:
        return None
    horas = Decimal(delta.total_seconds() / 3600)
    return float(horas.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def _organizacion_publica(org: Organizacion | None) -> str:
    """Evita publicar contactos o nombres de donantes privados no verificados."""
    if org is None:
        return "Organización no publicada"
    if org.tipo == Organizacion.Tipo.DONANTE_PRIVADO and not org.verificada:
        return "Donante privado"
    return org.nombre


def _foto_publica(request, envio: Envio | None) -> str | None:
    if not envio:
        return None

    foto_lista = envio.fotos.filter(estado="lista", comprimida__isnull=False).first()
    if foto_lista and foto_lista.comprimida:
        return request.build_absolute_uri(foto_lista.comprimida.url)

    if envio.foto_confirmacion_ref:
        return envio.foto_confirmacion_ref

    return None


def _etapa(etapa: str, activa: bool, fecha=None, gps=None, foto_url=None):
    data = {
        "estado": etapa,
        "activo": activa,
        "fecha": fecha.isoformat() if fecha else None,
    }
    if gps:
        data["gps"] = gps
    if foto_url:
        data["foto_url"] = foto_url
    return data


def _donacion_publica(request, donacion: Donacion) -> dict:
    asignaciones = list(
        donacion.asignacion_set.select_related(
            "necesidad__centro",
            "necesidad__item",
            "organizacion_responsable",
        ).order_by("claim_ts_servidor", "created_at")
    )
    asignacion = asignaciones[0] if asignaciones else None
    envios = []
    if asignacion:
        envios = list(asignacion.envio_set.all().order_by("created_at"))
    envio = envios[-1] if envios else None

    centro = asignacion.necesidad.centro if asignacion else None
    necesidad = asignacion.necesidad if asignacion else None
    envio_entregado = envio if envio and envio.estado == Envio.Estado.ENTREGADO else None

    pipeline = [
        _etapa(Donacion.Estado.REGISTRADA, True, donacion.created_at),
        _etapa(
            Donacion.Estado.ASIGNADA,
            asignacion is not None,
            asignacion.claim_ts_servidor or asignacion.created_at if asignacion else None,
        ),
        _etapa(
            Donacion.Estado.EN_TRANSITO,
            bool(envio and envio.estado in {Envio.Estado.EN_TRANSITO, Envio.Estado.ENTREGADO}),
            envio.created_at if envio else None,
        ),
        _etapa(
            Donacion.Estado.ENTREGADA,
            envio_entregado is not None,
            envio_entregado.timestamp_entrega or envio_entregado.updated_at if envio_entregado else None,
            gps=point_a_dict(envio_entregado.geolocalizacion_entrega)
            if envio_entregado
            else None,
            foto_url=_foto_publica(request, envio_entregado),
        ),
        _etapa(Donacion.Estado.EN_USO, donacion.estado == Donacion.Estado.EN_USO, donacion.updated_at),
    ]

    return {
        "id": str(donacion.id),
        "item": donacion.item.nombre,
        "categoria": donacion.item.categoria,
        "cantidad": donacion.cantidad,
        "unidad": donacion.item.unidad,
        "condicion": donacion.condicion,
        "estado_actual": donacion.estado,
        "donante": _organizacion_publica(donacion.donante),
        "ubicacion_origen": {
            "estado": donacion.ubicacion_texto or None,
            "gps": point_a_dict(donacion.ubicacion_actual),
        },
        "destino": {
            "centro": centro.nombre if centro else None,
            "estado": centro.estado if centro else None,
            "municipio": centro.municipio if centro else None,
            "gps": point_a_dict(centro.geolocalizacion) if centro else None,
        },
        "necesidad": {
            "id": str(necesidad.id) if necesidad else None,
            "item": necesidad.item.nombre if necesidad else None,
            "nivel_triage": necesidad.nivel_triage if necesidad else None,
            "estado": necesidad.estado if necesidad else None,
        },
        "organizacion_responsable": _organizacion_publica(asignacion.organizacion_responsable)
        if asignacion
        else None,
        "pipeline": pipeline,
        "actualizado_en": donacion.updated_at.isoformat(),
    }


@api_view(["GET"])
@permission_classes([AllowAny])
def transparencia_resumen(request):
    """Métricas públicas agregadas, sin PII ni contactos operativos."""
    necesidades = Necesidad.objects.select_related("centro")
    donaciones = Donacion.objects.filter(estado__in=ESTADOS_PUBLICABLES)

    cobertura_por_municipio = list(
        necesidades.values("centro__estado", "centro__municipio")
        .annotate(
            total=Count("id"),
            abiertas=Count("id", filter=F("estado").in_([Necesidad.Estado.ABIERTA, Necesidad.Estado.PARCIAL])),
            cubiertas=Count("id", filter=F("estado").in_([Necesidad.Estado.CUBIERTA])),
        )
        .order_by("centro__estado", "centro__municipio")
    )

    duracion_respuesta = ExpressionWrapper(
        F("timestamp_entrega") - F("asignacion__necesidad__created_at"),
        output_field=fields.DurationField(),
    )
    tiempo_promedio = (
        Envio.objects.filter(
            estado=Envio.Estado.ENTREGADO,
            timestamp_entrega__isnull=False,
        )
        .annotate(tiempo_respuesta=duracion_respuesta)
        .aggregate(promedio=Avg("tiempo_respuesta"))["promedio"]
    )

    return Response(
        {
            "actualizado_en": timezone.now().isoformat(),
            "metricas": {
                "necesidades_abiertas": necesidades.filter(
                    estado__in=[Necesidad.Estado.ABIERTA, Necesidad.Estado.PARCIAL]
                ).count(),
                "necesidades_cubiertas": necesidades.filter(
                    estado=Necesidad.Estado.CUBIERTA
                ).count(),
                "donaciones_entregadas": donaciones.filter(
                    estado__in=[Donacion.Estado.ENTREGADA, Donacion.Estado.EN_USO]
                ).count(),
                "donaciones_en_pipeline": donaciones.count(),
                "tiempo_respuesta_promedio_horas": _redondear_horas(tiempo_promedio),
            },
            "cobertura_por_municipio": [
                {
                    "estado": fila["centro__estado"],
                    "municipio": fila["centro__municipio"],
                    "total_necesidades": fila["total"],
                    "abiertas": fila["abiertas"],
                    "cubiertas": fila["cubiertas"],
                }
                for fila in cobertura_por_municipio
            ],
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def transparencia_donaciones(request):
    """Trazabilidad pública por donación, filtrada para donantes y prensa."""
    limite = min(int(request.query_params.get("limite", 100)), 200)
    donaciones = (
        Donacion.objects.filter(estado__in=ESTADOS_PUBLICABLES)
        .select_related("donante", "item")
        .prefetch_related(
            "asignacion_set__necesidad__centro",
            "asignacion_set__necesidad__item",
            "asignacion_set__organizacion_responsable",
            "asignacion_set__envio_set__fotos",
        )
        .order_by("-updated_at")[:limite]
    )

    return Response(
        {
            "actualizado_en": timezone.now().isoformat(),
            "resultados": [_donacion_publica(request, donacion) for donacion in donaciones],
        }
    )
