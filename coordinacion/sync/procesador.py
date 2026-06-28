import hashlib
import json
from typing import Any

from django.contrib.gis.db.models import PointField
from django.db import transaction
from django.utils import timezone

from coordinacion.geo import normalizar_point, point_a_dict
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


def preparar_datos_modelo(modelo, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Permite que el cliente offline envíe relaciones como `centro`, `item`, etc.
    con el UUID de la FK. Django necesita asignarlas como `centro_id`, `item_id`
    cuando no se está pasando una instancia del modelo relacionado.

    También normaliza PointField para que sync acepte GeoJSON, listas [lon, lat],
    dicts {lat, lon} y geopoint de KoBo en texto.
    """
    datos = payload.copy()
    for campo in modelo._meta.fields:
        if campo.is_relation and campo.many_to_one and campo.name in datos:
            datos[f"{campo.name}_id"] = datos.pop(campo.name)
        elif isinstance(campo, PointField) and campo.name in datos:
            datos[campo.name] = normalizar_point(datos[campo.name])
    return datos


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

    try:
        datos = preparar_datos_modelo(modelo, payload)
    except (TypeError, ValueError) as exc:
        return {
            "idempotency_key": idempotency_key,
            "estado": "conflicto",
            "mensaje": f"Coordenadas inválidas: {exc}",
        }

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


def serializar_objeto_sync(objeto) -> dict[str, Any]:
    """
    Convierte un modelo en un diccionario simple para sincronización offline.
    Evita depender de serializers DRF dentro del motor sync.
    """
    data = {
        "id": str(objeto.id),
        "created_at": objeto.created_at.isoformat(),
        "updated_at": objeto.updated_at.isoformat(),
        "version": objeto.version,
    }

    if isinstance(objeto, Organizacion):
        data.update(
            {
                "nombre": objeto.nombre,
                "tipo": objeto.tipo,
                "contacto": objeto.contacto,
                "verificada": objeto.verificada,
                "activa": objeto.activa,
            }
        )

    elif isinstance(objeto, Catalogo):
        data.update(
            {
                "codigo": objeto.codigo,
                "nombre": objeto.nombre,
                "categoria": objeto.categoria,
                "unidad": objeto.unidad,
                "activo": objeto.activo,
            }
        )

    elif isinstance(objeto, CentroSalud):
        data.update(
            {
                "nombre": objeto.nombre,
                "tipo": objeto.tipo,
                "estado_operativo": objeto.estado_operativo,
                "geolocalizacion": point_a_dict(objeto.geolocalizacion),
                "estado": objeto.estado,
                "municipio": objeto.municipio,
                "tiene_electricidad": objeto.tiene_electricidad,
                "tiene_agua": objeto.tiene_agua,
                "tiene_oxigeno": objeto.tiene_oxigeno,
                "tiene_personal_tecnico": objeto.tiene_personal_tecnico,
                "contacto_responsable": objeto.contacto_responsable,
                "ultima_actualizacion": objeto.ultima_actualizacion.isoformat()
                if objeto.ultima_actualizacion
                else None,
            }
        )

    elif isinstance(objeto, Necesidad):
        data.update(
            {
                "centro": str(objeto.centro_id),
                "item": str(objeto.item_id),
                "cantidad_solicitada": objeto.cantidad_solicitada,
                "cantidad_cubierta": objeto.cantidad_cubierta,
                "nivel_triage": objeto.nivel_triage,
                "requisitos_operacion": objeto.requisitos_operacion,
                "estado": objeto.estado,
                "reportada_por": str(objeto.reportada_por_id),
            }
        )

    elif isinstance(objeto, Donacion):
        data.update(
            {
                "donante": str(objeto.donante_id),
                "item": str(objeto.item_id),
                "cantidad": objeto.cantidad,
                "condicion": objeto.condicion,
                "vencimiento": objeto.vencimiento.isoformat()
                if objeto.vencimiento
                else None,
                "certificacion": objeto.certificacion,
                "ubicacion_actual": point_a_dict(objeto.ubicacion_actual),
                "ubicacion_texto": objeto.ubicacion_texto,
                "estado": objeto.estado,
            }
        )

    elif isinstance(objeto, Asignacion):
        data.update(
            {
                "necesidad": str(objeto.necesidad_id),
                "donacion": str(objeto.donacion_id),
                "cantidad_asignada": objeto.cantidad_asignada,
                "organizacion_responsable": str(objeto.organizacion_responsable_id),
                "estado_claim": objeto.estado_claim,
                "claim_ts_cliente": objeto.claim_ts_cliente.isoformat()
                if objeto.claim_ts_cliente
                else None,
                "claim_ts_servidor": objeto.claim_ts_servidor.isoformat()
                if objeto.claim_ts_servidor
                else None,
                "estado_logistico": objeto.estado_logistico,
            }
        )

    elif isinstance(objeto, Envio):
        data.update(
            {
                "asignacion": str(objeto.asignacion_id),
                "estado": objeto.estado,
                "responsable": objeto.responsable,
                "foto_confirmacion_ref": objeto.foto_confirmacion_ref,
                "geolocalizacion_entrega": point_a_dict(objeto.geolocalizacion_entrega),
                "geolocalizacion_entrega_texto": objeto.geolocalizacion_entrega_texto,
                "timestamp_entrega": objeto.timestamp_entrega.isoformat()
                if objeto.timestamp_entrega
                else None,
                "recibido_por": objeto.recibido_por,
                "notas": objeto.notas,
            }
        )

    return data


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
            serializar_objeto_sync(objeto) for objeto in queryset
        ]

    return respuesta
