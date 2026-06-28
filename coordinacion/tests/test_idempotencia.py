"""
Idempotencia de /sync (PROMPT_MAESTRO §4 regla de oro #4, §5).

Garantías verificadas:
- Un mismo idempotency_key reprocesado se descarta ('duplicado'), sin duplicar filas.
- Crear y luego actualizar por delta funciona y sube 'version'.
- Conflicto cuando la versión enviada es menor que la del servidor.
- Eventos mal formados (sin key, entidad no soportada, sin id) -> 'conflicto'.
"""
import uuid

import pytest

from coordinacion.models import Organizacion
from coordinacion.sync.procesador import procesar_evento_sync, procesar_lote_sync

pytestmark = pytest.mark.django_db


def _evento(entity="organizacion", payload=None, key=None):
    return {
        "idempotency_key": key or str(uuid.uuid4()),
        "entity": entity,
        "payload": payload or {},
    }


def test_alta_simple_crea_objeto():
    oid = str(uuid.uuid4())
    ev = _evento(payload={"id": oid, "nombre": "ONG Alfa", "tipo": "ong"})
    r = procesar_evento_sync(ev)
    assert r["estado"] == "ok"
    assert Organizacion.objects.filter(id=oid).count() == 1


def test_reintento_mismo_key_no_duplica():
    oid = str(uuid.uuid4())
    key = str(uuid.uuid4())
    ev = _evento(payload={"id": oid, "nombre": "ONG Beta", "tipo": "ong"}, key=key)

    r1 = procesar_evento_sync(ev)
    r2 = procesar_evento_sync(ev)  # ACK perdido + reintento

    assert r1["estado"] == "ok"
    assert r2["estado"] == "duplicado"
    assert Organizacion.objects.filter(id=oid).count() == 1


def test_lote_con_duplicado_interno():
    oid = str(uuid.uuid4())
    key = str(uuid.uuid4())
    ev = _evento(payload={"id": oid, "nombre": "ONG Gamma", "tipo": "ong"}, key=key)

    resultado = procesar_lote_sync([ev, ev])  # mismo evento dos veces en el lote
    estados = [r["estado"] for r in resultado["resultados"]]

    assert estados == ["ok", "duplicado"]
    assert Organizacion.objects.filter(id=oid).count() == 1


def test_actualizacion_por_delta_sube_version():
    oid = str(uuid.uuid4())
    procesar_evento_sync(
        _evento(payload={"id": oid, "nombre": "ONG Delta", "tipo": "ong"})
    )
    org = Organizacion.objects.get(id=oid)
    assert org.version == 1

    procesar_evento_sync(
        _evento(payload={"id": oid, "nombre": "ONG Delta v2", "tipo": "ong", "version": 1})
    )
    org.refresh_from_db()
    assert org.nombre == "ONG Delta v2"
    assert org.version == 2


def test_conflicto_por_version_menor():
    oid = str(uuid.uuid4())
    procesar_evento_sync(_evento(payload={"id": oid, "nombre": "ONG E", "tipo": "ong"}))
    # subir a version 2
    procesar_evento_sync(
        _evento(payload={"id": oid, "nombre": "ONG E2", "tipo": "ong", "version": 1})
    )
    # ahora llega un evento viejo con version 1 (< 2) -> conflicto
    r = procesar_evento_sync(
        _evento(payload={"id": oid, "nombre": "ONG vieja", "tipo": "ong", "version": 1})
    )
    assert r["estado"] == "conflicto"
    org = Organizacion.objects.get(id=oid)
    assert org.nombre == "ONG E2"  # no se piso con el valor viejo


def test_falta_idempotency_key():
    r = procesar_evento_sync({"entity": "organizacion", "payload": {"id": str(uuid.uuid4())}})
    assert r["estado"] == "conflicto"


def test_entidad_no_soportada():
    r = procesar_evento_sync(_evento(entity="paciente", payload={"id": str(uuid.uuid4())}))
    assert r["estado"] == "conflicto"


def test_payload_sin_id():
    r = procesar_evento_sync(_evento(payload={"nombre": "sin id", "tipo": "ong"}))
    assert r["estado"] == "conflicto"
