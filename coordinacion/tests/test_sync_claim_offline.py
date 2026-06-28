"""
Claim offline vía /sync (PROMPT_MAESTRO §5).

El claim no puede tratarse como una asignación común: debe pasar siempre por
reclamar_necesidad(), que bloquea la necesidad con select_for_update y arbitra
por orden de llegada al servidor.
"""
import uuid

import pytest

from coordinacion.models import Asignacion, Donacion, EventoSincronizado, Necesidad
from coordinacion.sync.procesador import procesar_evento_sync, procesar_lote_sync

pytestmark = pytest.mark.django_db


def _evento_claim(necesidad, donacion, organizacion, cantidad=5, key=None):
    return {
        "idempotency_key": str(key or uuid.uuid4()),
        "client_timestamp": "2026-06-28T10:00:00-04:00",
        "entity": "claim_necesidad",
        "payload": {
            "necesidad": str(necesidad.id),
            "donacion": str(donacion.id),
            "cantidad_asignada": cantidad,
            "organizacion_responsable": str(organizacion.id),
        },
    }


def test_claim_offline_por_sync_arbitra_y_confirma(necesidad, donacion, organizacion):
    resultado = procesar_evento_sync(
        _evento_claim(necesidad, donacion, organizacion, cantidad=5)
    )

    necesidad.refresh_from_db()
    donacion.refresh_from_db()

    assert resultado["estado"] == "ok"
    assert resultado["entity"] == "claim_necesidad"
    assert resultado["estado_claim"] == Asignacion.EstadoClaim.CONFIRMADA
    assert Asignacion.objects.count() == 1
    assert necesidad.cantidad_cubierta == 5
    assert necesidad.estado == Necesidad.Estado.PARCIAL
    assert donacion.cantidad == 5


def test_claim_offline_duplicado_por_sync_no_doble_asigna(
    necesidad, donacion, organizacion
):
    key = uuid.uuid4()
    evento = _evento_claim(necesidad, donacion, organizacion, cantidad=5, key=key)

    primero = procesar_evento_sync(evento)
    segundo = procesar_evento_sync(evento)

    necesidad.refresh_from_db()
    donacion.refresh_from_db()

    assert primero["estado"] == "ok"
    assert segundo["estado"] == "duplicado"
    assert segundo["resultado_original"] == "ok"
    assert Asignacion.objects.count() == 1
    assert necesidad.cantidad_cubierta == 5
    assert donacion.cantidad == 5


def test_claim_offline_superado_por_sync_no_crea_asignacion(
    necesidad, donacion, catalogo, organizacion
):
    donacion_b = Donacion.objects.create(
        donante=organizacion,
        item=catalogo,
        cantidad=10,
        condicion=Donacion.Condicion.NUEVO,
        estado=Donacion.Estado.DISPONIBLE,
    )

    resultado = procesar_lote_sync(
        [
            _evento_claim(necesidad, donacion, organizacion, cantidad=10),
            _evento_claim(necesidad, donacion_b, organizacion, cantidad=1),
        ]
    )

    estados = [r["estado"] for r in resultado["resultados"]]
    necesidad.refresh_from_db()
    donacion_b.refresh_from_db()

    assert estados == ["ok", "superada"]
    assert Asignacion.objects.count() == 1
    assert necesidad.estado == Necesidad.Estado.CUBIERTA
    assert necesidad.cantidad_cubierta == 10
    assert donacion_b.cantidad == 10
    assert donacion_b.estado == Donacion.Estado.DISPONIBLE


def test_sync_comun_no_permite_asignacion_confirmada_directa(
    necesidad, donacion, organizacion
):
    resultado = procesar_evento_sync(
        {
            "idempotency_key": str(uuid.uuid4()),
            "entity": "asignacion",
            "payload": {
                "id": str(uuid.uuid4()),
                "necesidad": str(necesidad.id),
                "donacion": str(donacion.id),
                "cantidad_asignada": 5,
                "organizacion_responsable": str(organizacion.id),
                "estado_claim": Asignacion.EstadoClaim.CONFIRMADA,
                "claim_ts_cliente": "2026-06-28T10:00:00-04:00",
                "estado_logistico": Asignacion.EstadoLogistico.PENDIENTE,
            },
        }
    )

    necesidad.refresh_from_db()
    donacion.refresh_from_db()

    assert resultado["estado"] == "conflicto"
    assert Asignacion.objects.count() == 0
    assert necesidad.cantidad_cubierta == 0
    assert donacion.cantidad == 10
    assert EventoSincronizado.objects.filter(
        idempotency_key=resultado["idempotency_key"], resultado="conflicto"
    ).exists()
