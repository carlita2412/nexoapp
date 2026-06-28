import uuid

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from coordinacion.auditoria import (
    ACCION_ADMINISTRAR_CATALOGO,
    ACCION_CONFIRMAR_ENTREGA,
    ACCION_CREAR_DONACION,
    ACCION_CREAR_NECESIDAD,
    ACCION_RECLAMAR_NECESIDAD,
    ACCION_SUBIR_FOTO,
)
from coordinacion.models import (
    Asignacion,
    Donacion,
    Envio,
    Necesidad,
    RegistroAuditoria,
    Usuario,
)
from coordinacion.sync.procesador import procesar_lote_sync

pytestmark = pytest.mark.django_db


GIF_1X1 = (
    b"GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00\xff\xff\xff,"
    b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


def test_audita_creacion_de_necesidad_por_api(
    autenticar,
    usuarios,
    centro,
    catalogo,
    organizacion,
):
    api = autenticar(usuarios[Usuario.Rol.CAMPO])

    respuesta = api.post(
        "/api/v1/necesidades/",
        {
            "centro": str(centro.id),
            "item": str(catalogo.id),
            "cantidad_solicitada": 3,
            "nivel_triage": Necesidad.NivelTriage.URGENTE,
            "reportada_por": str(organizacion.id),
        },
        format="json",
    )

    assert respuesta.status_code == 201
    auditoria = RegistroAuditoria.objects.get(accion=ACCION_CREAR_NECESIDAD)
    assert auditoria.entidad == "necesidad"
    assert str(auditoria.entidad_id) == respuesta.data["id"]
    assert auditoria.detalle["operacion"] == "create"
    assert auditoria.detalle["usuario"]["rol"] == Usuario.Rol.CAMPO


def test_audita_creacion_de_donacion_por_api(
    autenticar,
    usuarios,
    catalogo,
    organizacion,
):
    api = autenticar(usuarios[Usuario.Rol.CAMPO])

    respuesta = api.post(
        "/api/v1/donaciones/",
        {
            "donante": str(organizacion.id),
            "item": str(catalogo.id),
            "cantidad": 4,
            "condicion": Donacion.Condicion.NUEVO,
            "estado": Donacion.Estado.DISPONIBLE,
        },
        format="json",
    )

    assert respuesta.status_code == 201
    auditoria = RegistroAuditoria.objects.get(accion=ACCION_CREAR_DONACION)
    assert auditoria.entidad == "donacion"
    assert str(auditoria.entidad_id) == respuesta.data["id"]


def test_audita_claim_de_necesidad_por_api(
    autenticar,
    usuarios,
    necesidad,
    donacion,
    organizacion,
):
    api = autenticar(usuarios[Usuario.Rol.COORDINADOR])

    respuesta = api.post(
        f"/api/v1/necesidades/{necesidad.id}/claim/",
        {
            "donacion_id": str(donacion.id),
            "cantidad_asignada": 2,
            "organizacion_responsable_id": str(organizacion.id),
            "idempotency_key": str(uuid.uuid4()),
        },
        format="json",
    )

    assert respuesta.status_code == 201
    auditoria = RegistroAuditoria.objects.get(accion=ACCION_RECLAMAR_NECESIDAD)
    assert auditoria.entidad == "asignacion"
    assert auditoria.detalle["necesidad_id"] == str(necesidad.id)
    assert auditoria.detalle["cantidad_asignada"] == 2
    assert auditoria.detalle["estado_claim"] == Asignacion.EstadoClaim.CONFIRMADA


def test_audita_confirmacion_de_entrega_y_subida_de_foto(
    autenticar,
    usuarios,
    necesidad,
    donacion,
    organizacion,
    monkeypatch,
):
    api = autenticar(usuarios[Usuario.Rol.CAMPO])
    asignacion = Asignacion.objects.create(
        necesidad=necesidad,
        donacion=donacion,
        cantidad_asignada=1,
        organizacion_responsable=organizacion,
        estado_claim=Asignacion.EstadoClaim.CONFIRMADA,
        claim_ts_cliente=timezone.now(),
        claim_ts_servidor=timezone.now(),
    )

    respuesta_envio = api.post(
        "/api/v1/envios/",
        {
            "asignacion": str(asignacion.id),
            "estado": Envio.Estado.ENTREGADO,
            "responsable": "Equipo campo",
            "recibido_por": "Responsable centro",
            "timestamp_entrega": timezone.now().isoformat(),
        },
        format="json",
    )

    assert respuesta_envio.status_code == 201
    assert RegistroAuditoria.objects.filter(
        accion=ACCION_CONFIRMAR_ENTREGA,
        entidad="envio",
    ).exists()

    monkeypatch.setattr(
        "coordinacion.fotos.vistas.encolar_procesamiento",
        lambda foto_id: None,
    )
    imagen = SimpleUploadedFile("foto.gif", GIF_1X1, content_type="image/gif")
    respuesta_foto = api.post(
        "/api/v1/fotos/",
        {
            "idempotency_key": str(uuid.uuid4()),
            "envio": respuesta_envio.data["id"],
            "imagen": imagen,
        },
        format="multipart",
    )

    assert respuesta_foto.status_code == 202
    auditoria = RegistroAuditoria.objects.get(accion=ACCION_SUBIR_FOTO)
    assert auditoria.entidad == "foto"
    assert auditoria.detalle["envio_id"] == respuesta_envio.data["id"]


def test_audita_catalogos_y_sync_critico(
    autenticar,
    usuarios,
    catalogo,
    centro,
    organizacion,
):
    api = autenticar(usuarios[Usuario.Rol.ADMIN])

    respuesta = api.patch(
        f"/api/v1/catalogos/{catalogo.id}/",
        {"nombre": "Concentrador actualizado"},
        format="json",
    )

    assert respuesta.status_code == 200
    auditoria_catalogo = RegistroAuditoria.objects.get(
        accion=ACCION_ADMINISTRAR_CATALOGO
    )
    assert auditoria_catalogo.entidad == "catalogo"
    assert auditoria_catalogo.detalle["operacion"] == "update"

    necesidad_id = uuid.uuid4()
    resultado = procesar_lote_sync(
        [
            {
                "idempotency_key": uuid.uuid4(),
                "entity": "necesidad",
                "payload": {
                    "id": necesidad_id,
                    "centro": centro.id,
                    "item": catalogo.id,
                    "cantidad_solicitada": 1,
                    "nivel_triage": Necesidad.NivelTriage.CRITICO,
                    "reportada_por": organizacion.id,
                },
            }
        ],
        usuario=usuarios[Usuario.Rol.CAMPO],
    )

    assert resultado["resultados"][0]["estado"] == "ok"
    auditoria_sync = RegistroAuditoria.objects.filter(
        accion=ACCION_CREAR_NECESIDAD,
        detalle__origen="sync",
    ).get()
    assert str(auditoria_sync.entidad_id) == str(necesidad_id)
    assert auditoria_sync.detalle["usuario"]["rol"] == Usuario.Rol.CAMPO
