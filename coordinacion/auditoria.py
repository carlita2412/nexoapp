"""Utilidades para registrar auditoria operativa de acciones criticas."""
from __future__ import annotations

import uuid
from typing import Any

from django.utils import timezone

from .models import RegistroAuditoria


ACCION_CREAR_NECESIDAD = "crear_necesidad"
ACCION_CREAR_DONACION = "crear_donacion"
ACCION_RECLAMAR_NECESIDAD = "reclamar_necesidad"
ACCION_CONFIRMAR_ENTREGA = "confirmar_entrega"
ACCION_SUBIR_FOTO = "subir_foto"
ACCION_ADMINISTRAR_CATALOGO = "administrar_catalogo"
ACCION_ADMINISTRAR_ORGANIZACION = "administrar_organizacion"


ACCIONES_CRITICAS_SYNC = {
    ("necesidad", "crear"): ACCION_CREAR_NECESIDAD,
    ("donacion", "crear"): ACCION_CREAR_DONACION,
    ("claim_necesidad", "reclamar"): ACCION_RECLAMAR_NECESIDAD,
    ("envio", "crear"): ACCION_CONFIRMAR_ENTREGA,
    ("envio", "actualizar"): ACCION_CONFIRMAR_ENTREGA,
    ("catalogo", "crear"): ACCION_ADMINISTRAR_CATALOGO,
    ("catalogo", "actualizar"): ACCION_ADMINISTRAR_CATALOGO,
    ("organizacion", "crear"): ACCION_ADMINISTRAR_ORGANIZACION,
    ("organizacion", "actualizar"): ACCION_ADMINISTRAR_ORGANIZACION,
}


def _uuid_o_none(valor: Any) -> uuid.UUID | None:
    if valor in (None, ""):
        return None
    try:
        return uuid.UUID(str(valor))
    except (TypeError, ValueError, AttributeError):
        return None


def _detalle_usuario(usuario) -> dict[str, Any]:
    if not usuario or not getattr(usuario, "is_authenticated", False):
        return {"autenticado": False}

    return {
        "autenticado": True,
        "id": str(getattr(usuario, "id", "")),
        "username": getattr(usuario, "username", ""),
        "rol": getattr(usuario, "rol", ""),
        "organizacion_id": str(getattr(usuario, "organizacion_id", "") or ""),
    }


def registrar_auditoria(
    *,
    usuario=None,
    accion: str,
    entidad: str,
    entidad_id=None,
    detalle: dict[str, Any] | None = None,
) -> RegistroAuditoria:
    """
    Crea una entrada de RegistroAuditoria para trazabilidad multi-organizacion.

    El modelo actual guarda `usuario_id` como UUID, pero `Usuario` hereda el ID
    numerico de Django. Para no romper compatibilidad, solo se llena
    `usuario_id` cuando el identificador es UUID; siempre se guarda el usuario
    operativo dentro de `detalle.usuario`.
    """
    detalle_final = dict(detalle or {})
    detalle_final.setdefault("usuario", _detalle_usuario(usuario))
    detalle_final.setdefault("registrado_en", timezone.now().isoformat())

    return RegistroAuditoria.objects.create(
        usuario_id=_uuid_o_none(getattr(usuario, "id", None)),
        accion=accion,
        entidad=entidad,
        entidad_id=_uuid_o_none(entidad_id),
        detalle=detalle_final,
    )


def accion_sync_para(entidad: str, operacion: str) -> str | None:
    return ACCIONES_CRITICAS_SYNC.get((entidad, operacion))
