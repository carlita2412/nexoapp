from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.conf import settings
from django.db import transaction

from coordinacion.kobo.cliente import ClienteKobo
from coordinacion.kobo.mapeadores import (
    MapeoKoboError,
    mapear_submission,
    obtener_submission_time,
    obtener_submission_uuid,
)
from coordinacion.models import KoboCursor
from coordinacion.sync.procesador import procesar_evento_sync


TIPOS_KOBO = {"necesidad", "donacion"}


@dataclass
class ResultadoIngestaKobo:
    tipo: str
    recibidos: int = 0
    procesados: int = 0
    duplicados: int = 0
    omitidos: int = 0
    errores: list[dict[str, Any]] = field(default_factory=list)

    def como_dict(self) -> dict[str, Any]:
        return {
            "tipo": self.tipo,
            "recibidos": self.recibidos,
            "procesados": self.procesados,
            "duplicados": self.duplicados,
            "omitidos": self.omitidos,
            "errores": self.errores,
        }


def obtener_asset_uid(tipo: str) -> str:
    if tipo == "necesidad":
        return getattr(settings, "KOBO_ASSET_NECESIDADES", "")
    if tipo == "donacion":
        return getattr(settings, "KOBO_ASSET_DONACIONES", "")
    raise ValueError(f"Tipo KoBo no soportado: {tipo}")


def obtener_o_crear_cursor(tipo: str, asset_uid: str) -> KoboCursor:
    cursor, _ = KoboCursor.objects.get_or_create(
        tipo_formulario=tipo,
        defaults={"asset_uid": asset_uid},
    )
    if asset_uid and cursor.asset_uid != asset_uid:
        cursor.asset_uid = asset_uid
        cursor.save(update_fields=["asset_uid", "actualizado_en"])
    return cursor


@transaction.atomic
def avanzar_cursor(cursor: KoboCursor, submission: dict[str, Any]) -> None:
    cursor.ultimo_submission_time = obtener_submission_time(submission)
    cursor.ultimo_uuid = obtener_submission_uuid(submission)
    cursor.save(update_fields=["ultimo_submission_time", "ultimo_uuid", "actualizado_en"])


def procesar_submission_kobo(tipo: str, submission: dict[str, Any]) -> dict[str, Any]:
    evento = mapear_submission(tipo, submission)
    return procesar_evento_sync(evento)


def ingestar_tipo_kobo(
    tipo: str,
    *,
    cliente: ClienteKobo | None = None,
) -> dict[str, Any]:
    if tipo not in TIPOS_KOBO:
        raise ValueError(f"Tipo KoBo no soportado: {tipo}")

    asset_uid = obtener_asset_uid(tipo)
    cursor = obtener_o_crear_cursor(tipo, asset_uid)
    cliente = cliente or ClienteKobo()
    resultado = ResultadoIngestaKobo(tipo=tipo)

    submissions = cliente.obtener_submissions(
        asset_uid=asset_uid,
        desde=cursor.ultimo_submission_time,
    )
    resultado.recibidos = len(submissions)

    for submission in submissions:
        try:
            respuesta = procesar_submission_kobo(tipo, submission)
            estado = respuesta.get("estado")
            if estado == "duplicado":
                resultado.duplicados += 1
            elif estado == "ok":
                resultado.procesados += 1
            else:
                resultado.omitidos += 1
                resultado.errores.append(
                    {
                        "uuid": submission.get("_uuid"),
                        "estado": estado,
                        "mensaje": respuesta.get("mensaje"),
                    }
                )
            avanzar_cursor(cursor, submission)
        except MapeoKoboError as exc:
            resultado.omitidos += 1
            resultado.errores.append({"uuid": submission.get("_uuid"), "mensaje": str(exc)})
            if submission.get("_submission_time") and submission.get("_uuid"):
                avanzar_cursor(cursor, submission)

    return resultado.como_dict()


def ingestar_todo_kobo() -> dict[str, Any]:
    return {
        "necesidad": ingestar_tipo_kobo("necesidad"),
        "donacion": ingestar_tipo_kobo("donacion"),
    }
