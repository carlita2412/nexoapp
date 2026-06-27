import hashlib
import json
from typing import Any

from django.db import transaction
from django.utils import timezone

from coordinacion.models import (
    Asignacion,
    Catalogo,
    CentroSalud,
    Donacion,
    Envio,
    EventoSincronizado,
    Necesidad,
    Organizacion,
)


MODELOS_SINCRONIZABLES = {
    "organizacion": Organizacion,
    "catalogo": Catalogo,
    "centro_salud": CentroSalud,
    "necesidad": Necesidad,
    "donacion": Donacion,
    "asignacion": Asignacion,
    "envio": Envio,
}


def generar_hash_payload(payload: dict[str, Any]) -> str:
    texto = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def normalizar_entidad(nombre: str) -> str:
    return nombre.strip().lower()


@transaction.atomic
def procesar_evento_sync(evento: dict[str, Any]) -> dict[str, Any]:
    idempotency_key = evento.get("idempotency_key")
    entidad = normalizar_entidad(evento.get("entity", ""))
    payload = evento.get("payload", {})

    if not idempotency_key:
        return {
            "idempotency_key": None,
            "estado": "conflicto",
            "mensaje": "Falta idempotency_key.",
        }

    if entidad not in MODELOS_SINCRONIZABLES:
        return {
            "idempotency_key": idempotency_key,
            "estado": "conflicto",
            "mensaje": f"Entidad no soportada: {entidad}.",
        }

    if not isinstance(payload, dict):
        return {
            "idempotency_key": idempotency_key,
            "estado": "conflicto",
            "mensaje": "Payload inválido.",
        }

    evento_existente = EventoSincronizado.objects.filter(
        idempotency_key=idempotency_key
    ).first()

    if evento_existente:
        return {
            "idempotency_key": idempotency_key,
            "estado": "duplicado",
            "mensaje": "Evento ya procesado anteriormente.",
            "entity": evento_existente.entity,
            "entity_id": str(evento_existente.entity_id)
            if evento_existente.entity_id
            else None,
        }

    modelo = MODELOS_SINCRONIZABLES[entidad]
    payload_hash = generar_hash_payload(payload)

    entity_id = payload.get("id")

    if not entity_id:
        return {
            "idempotency_key": idempotency_key,
            "estado": "conflicto",
            "mensaje": "El payload debe incluir id.",
        }

    datos = payload.copy()
    version_cliente = datos.pop("version", None)

    objeto_existente = modelo.objects.filter(id=entity_id).first()

    if objeto_existente:
        if version_cliente is not None and version_cliente < objeto_existente.version:
            EventoSincronizado.objects.create(
                idempotency_key=idempotency_key,
                entity=entidad,
                entity_id=entity_id,
                resultado="conflicto",
                payload_hash=payload_hash,
            )

            return {
                "idempotency_key": idempotency_key,
                "estado": "conflicto",
                "mensaje": "La versión enviada es menor que la versión del servidor.",
                "entity": entidad,
                "entity_id": str(entity_id),
            }

        for campo, valor in datos.items():
            if campo != "id" and hasattr(objeto_existente, campo):
                setattr(objeto_existente, campo, valor)

        objeto_existente.version += 1
        objeto_existente.save()

        resultado = "ok"
        objeto = objeto_existente

    else:
        objeto = modelo.objects.create(**datos)
        resultado = "ok"

    EventoSincronizado.objects.create(
        idempotency_key=idempotency_key,
        entity=entidad,
        entity_id=objeto.id,
        resultado=resultado,
        payload_hash=payload_hash,
    )

    return {
        "idempotency_key": idempotency_key,
        "estado": resultado,
        "mensaje": "Evento procesado.",
        "entity": entidad,
        "entity_id": str(objeto.id),
    }


def procesar_lote_sync(eventos: list[dict[str, Any]]) -> dict[str, Any]:
    resultados = []

    for evento in eventos:
        resultado = procesar_evento_sync(evento)
        resultados.append(resultado)

    return {
        "cursor": timezone.now().isoformat(),
        "resultados": resultados,
    }


def obtener_deltas(desde=None) -> dict[str, Any]:
    modelos = {
        "organizaciones": Organizacion,
        "catalogos": Catalogo,
        "centros_salud": CentroSalud,
        "necesidades": Necesidad,
        "donaciones": Donacion,
        "asignaciones": Asignacion,
        "envios": Envio,
    }

    respuesta = {
        "cursor": timezone.now().isoformat(),
        "deltas": {},
    }

    for nombre, modelo in modelos.items():
        queryset = modelo.objects.all().order_by("updated_at")

        if desde:
            queryset = queryset.filter(updated_at__gt=desde)

        respuesta["deltas"][nombre] = [
            {
                "id": str(objeto.id),
                "version": objeto.version,
                "updated_at": objeto.updated_at.isoformat(),
            }
            for objeto in queryset
        ]

    return respuesta