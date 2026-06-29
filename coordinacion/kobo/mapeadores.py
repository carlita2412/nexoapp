from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from coordinacion.geo import normalizar_point
from coordinacion.kobo.contrato import CONTRATO_KOBO
from coordinacion.models import Catalogo, CentroSalud, Donacion, Necesidad, Organizacion

NAMESPACE_KOBO = uuid.UUID("6c56b443-0ad2-4af7-9668-a375ff3ebf20")
NIVELES_TRIAGE_VALIDOS = {choice[0] for choice in Necesidad.NivelTriage.choices}
CONDICIONES_DONACION_VALIDAS = {choice[0] for choice in Donacion.Condicion.choices}


class MapeoKoboError(ValueError):
    pass


def _buscar_clave_kobo(submission: dict[str, Any], clave: str) -> Any:
    """
    KoBo devuelve campos dentro de grupos XLSForm como `grupo/campo`.
    El contrato Nexo usa el nombre final (`campo`) para que el backend no dependa
    de la estructura visual del formulario.
    """
    if clave in submission:
        return submission[clave]

    sufijo = f"/{clave}"
    for nombre, valor in submission.items():
        if nombre.endswith(sufijo):
            return valor
    return None


def _valor(submission: dict[str, Any], *claves: str, default: Any = None) -> Any:
    for clave in claves:
        valor = _buscar_clave_kobo(submission, clave)
        if valor not in (None, ""):
            return valor
    return default


def _tiene_algun_campo(submission: dict[str, Any], claves: tuple[str, ...]) -> bool:
    return any(_valor(submission, clave) not in (None, "") for clave in claves)


def _validar_campos_requeridos(tipo: str, submission: dict[str, Any]) -> None:
    faltantes = []
    for campo in CONTRATO_KOBO[tipo]:
        if campo.requerido and not _tiene_algun_campo(submission, campo.nombres_aceptados):
            faltantes.append("/".join(campo.nombres_aceptados))

    if tipo == "necesidad" and not (
        _tiene_algun_campo(submission, ("reportada_por_id", "organizacion_id", "reportada_por"))
        or _tiene_algun_campo(
            submission,
            ("reportada_por_nombre", "organizacion_nombre", "nombre_organizacion"),
        )
    ):
        faltantes.append("reportada_por_id o reportada_por_nombre")

    if tipo == "donacion" and not (
        _tiene_algun_campo(submission, ("donante_id", "organizacion_id", "donante"))
        or _tiene_algun_campo(
            submission,
            ("donante_nombre", "organizacion_nombre", "nombre_organizacion"),
        )
    ):
        faltantes.append("donante_id o donante_nombre")

    if faltantes:
        raise MapeoKoboError(
            f"Submission KoBo de {tipo} incompleta. Faltan campos: {', '.join(faltantes)}."
        )


def validar_submission_kobo(tipo: str, submission: dict[str, Any]) -> None:
    if tipo not in CONTRATO_KOBO:
        raise MapeoKoboError(f"Tipo KoBo no soportado: {tipo}")
    _validar_campos_requeridos(tipo, submission)


def _uuid_submission(submission: dict[str, Any]) -> str:
    valor = _valor(submission, "_uuid", "uuid", "submission_uuid")
    if not valor:
        raise MapeoKoboError("Submission sin _uuid.")
    return str(valor)


def _submission_time(submission: dict[str, Any]) -> datetime:
    valor = _valor(submission, "_submission_time", "submission_time")
    fecha = parse_datetime(str(valor)) if valor else None
    if not fecha:
        return timezone.now()
    if timezone.is_naive(fecha):
        return timezone.make_aware(fecha, timezone=timezone.utc)
    return fecha


def _uuid_estable(tipo: str, submission_uuid: str) -> str:
    return str(uuid.uuid5(NAMESPACE_KOBO, f"{tipo}:{submission_uuid}"))


def _idempotency_key(tipo: str, submission_uuid: str) -> str:
    return str(uuid.uuid5(NAMESPACE_KOBO, f"kobo:{tipo}:{submission_uuid}:v1"))


def _entero(valor: Any, campo: str) -> int:
    try:
        numero = int(float(valor))
    except (TypeError, ValueError) as exc:
        raise MapeoKoboError(f"{campo} debe ser numérico.") from exc
    if numero <= 0:
        raise MapeoKoboError(f"{campo} debe ser mayor a cero.")
    return numero


def _booleano(valor: Any) -> bool:
    if isinstance(valor, bool):
        return valor
    return str(valor).strip().lower() in {"1", "true", "si", "sí", "yes", "y"}


def _punto(valor: Any, campo: str):
    try:
        punto = normalizar_point(valor)
    except (TypeError, ValueError) as exc:
        raise MapeoKoboError(f"{campo} contiene coordenadas inválidas.") from exc
    if punto is None:
        raise MapeoKoboError(f"{campo} es obligatorio y debe contener coordenadas válidas.")
    return punto


def _catalogo(submission: dict[str, Any]) -> Catalogo:
    item_id = _valor(submission, "item_id", "catalogo_id")
    if item_id:
        try:
            return Catalogo.objects.get(id=item_id)
        except Catalogo.DoesNotExist as exc:
            raise MapeoKoboError(f"Catálogo no existe: {item_id}") from exc

    codigo = _valor(submission, "item_codigo", "codigo_item", "item")
    if not codigo:
        raise MapeoKoboError("Falta item_codigo o item_id.")
    try:
        return Catalogo.objects.get(codigo=str(codigo).strip())
    except Catalogo.DoesNotExist as exc:
        raise MapeoKoboError(f"Catálogo no existe: {codigo}") from exc


def _centro(submission: dict[str, Any]) -> CentroSalud:
    centro_id = _valor(submission, "centro_id", "centro_salud_id", "centro")
    if not centro_id:
        raise MapeoKoboError("Falta centro_id.")
    try:
        return CentroSalud.objects.get(id=centro_id)
    except CentroSalud.DoesNotExist as exc:
        raise MapeoKoboError(f"Centro de salud no existe: {centro_id}") from exc


def _organizacion(submission: dict[str, Any], *, campo_id: str, campo_nombre: str) -> Organizacion:
    organizacion_id = _valor(submission, campo_id, "organizacion_id", "reportada_por", "donante")
    if organizacion_id:
        try:
            return Organizacion.objects.get(id=organizacion_id)
        except Organizacion.DoesNotExist as exc:
            raise MapeoKoboError(f"Organización no existe: {organizacion_id}") from exc

    nombre = _valor(submission, campo_nombre, "organizacion_nombre", "nombre_organizacion")
    if not nombre:
        raise MapeoKoboError("Falta organización.")
    organizacion, _ = Organizacion.objects.get_or_create(
        nombre=str(nombre).strip(),
        defaults={"tipo": Organizacion.Tipo.ONG, "verificada": False, "activa": True},
    )
    return organizacion


def _nivel_triage(submission: dict[str, Any]) -> str:
    valor = str(
        _valor(submission, "nivel_triage", "triage", default=Necesidad.NivelTriage.IMPORTANTE)
    ).strip()
    if valor not in NIVELES_TRIAGE_VALIDOS:
        raise MapeoKoboError(
            "nivel_triage inválido. Usa: " + ", ".join(sorted(NIVELES_TRIAGE_VALIDOS))
        )
    return valor


def _condicion_donacion(submission: dict[str, Any]) -> str:
    valor = str(_valor(submission, "condicion", default=Donacion.Condicion.NUEVO)).strip()
    if valor not in CONDICIONES_DONACION_VALIDAS:
        raise MapeoKoboError(
            "condicion inválida. Usa: " + ", ".join(sorted(CONDICIONES_DONACION_VALIDAS))
        )
    return valor


def mapear_necesidad(submission: dict[str, Any]) -> dict[str, Any]:
    validar_submission_kobo("necesidad", submission)
    submission_uuid = _uuid_submission(submission)
    centro = _centro(submission)
    item = _catalogo(submission)
    reportada_por = _organizacion(
        submission,
        campo_id="reportada_por_id",
        campo_nombre="reportada_por_nombre",
    )

    payload = {
        "id": _uuid_estable("necesidad", submission_uuid),
        "centro": str(centro.id),
        "item": str(item.id),
        "cantidad_solicitada": _entero(
            _valor(submission, "cantidad_solicitada", "cantidad", default=1),
            "cantidad_solicitada",
        ),
        "cantidad_cubierta": 0,
        "nivel_triage": _nivel_triage(submission),
        "requisitos_operacion": {
            "requiere_electricidad": _booleano(_valor(submission, "requiere_electricidad", default=False)),
            "requiere_oxigeno": _booleano(_valor(submission, "requiere_oxigeno", default=False)),
            "requiere_personal_entrenado": _booleano(
                _valor(submission, "requiere_personal_entrenado", "requiere_personal_tecnico", default=False)
            ),
            "requiere_insumos": _booleano(_valor(submission, "requiere_insumos", default=False)),
        },
        "estado": Necesidad.Estado.ABIERTA,
        "reportada_por": str(reportada_por.id),
        "version": 1,
    }

    return {
        "idempotency_key": _idempotency_key("necesidad", submission_uuid),
        "client_timestamp": _submission_time(submission).isoformat(),
        "entity": "necesidad",
        "payload": payload,
    }


def mapear_donacion(submission: dict[str, Any]) -> dict[str, Any]:
    validar_submission_kobo("donacion", submission)
    submission_uuid = _uuid_submission(submission)
    item = _catalogo(submission)
    donante = _organizacion(
        submission,
        campo_id="donante_id",
        campo_nombre="donante_nombre",
    )
    vencimiento = _valor(submission, "vencimiento", "fecha_vencimiento")
    ubicacion = _valor(submission, "ubicacion_actual", "geopoint", "geolocalizacion", default="")

    payload = {
        "id": _uuid_estable("donacion", submission_uuid),
        "donante": str(donante.id),
        "item": str(item.id),
        "cantidad": _entero(_valor(submission, "cantidad", default=1), "cantidad"),
        "condicion": _condicion_donacion(submission),
        "vencimiento": parse_date(str(vencimiento)) if vencimiento else None,
        "certificacion": _valor(submission, "certificacion", default=""),
        "ubicacion_actual": _punto(ubicacion, "ubicacion_actual"),
        "ubicacion_texto": _valor(submission, "ubicacion_texto", "direccion", default=""),
        "estado": Donacion.Estado.DISPONIBLE,
        "version": 1,
    }

    return {
        "idempotency_key": _idempotency_key("donacion", submission_uuid),
        "client_timestamp": _submission_time(submission).isoformat(),
        "entity": "donacion",
        "payload": payload,
    }


def mapear_submission(tipo: str, submission: dict[str, Any]) -> dict[str, Any]:
    if tipo == "necesidad":
        return mapear_necesidad(submission)
    if tipo == "donacion":
        return mapear_donacion(submission)
    raise MapeoKoboError(f"Tipo KoBo no soportado: {tipo}")


def obtener_submission_time(submission: dict[str, Any]) -> datetime:
    return _submission_time(submission)


def obtener_submission_uuid(submission: dict[str, Any]) -> str:
    return _uuid_submission(submission)
