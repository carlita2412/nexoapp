"""
Fotos de entrega: compresión, subida en cola, idempotencia y permisos.

Reglas verificadas:
- La compresión deja la foto < 100 KB (§2), aun con una imagen enorme.
- La subida es multipart, devuelve 202 y encola el procesamiento.
- Procesar deja la foto 'lista', borra el original y fija foto_confirmacion_ref.
- Idempotencia: subir con la misma key no crea otra foto.
- Subida enorme se rechaza (413).
- Solo roles operativos suben; lectura no.
"""
import uuid
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from coordinacion.fotos.compresion import comprimir_a_objetivo
from coordinacion.fotos.tareas import procesar_foto
from coordinacion.models import Asignacion, Envio, Foto, Usuario

pytestmark = pytest.mark.django_db


def _imagen_jpeg(ancho=2400, alto=1600, color=(120, 60, 30)) -> bytes:
    img = Image.new("RGB", (ancho, alto), color)
    # algo de textura para que no comprima a casi nada
    px = img.load()
    for y in range(0, alto, 3):
        for x in range(0, ancho, 3):
            px[x, y] = ((x * 7) % 256, (y * 5) % 256, (x + y) % 256)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


@pytest.fixture
def envio(db, necesidad, donacion, organizacion):
    asig = Asignacion.objects.create(
        necesidad=necesidad,
        donacion=donacion,
        cantidad_asignada=1,
        organizacion_responsable=organizacion,
        claim_ts_cliente="2026-06-01T10:00:00Z",
    )
    return Envio.objects.create(asignacion=asig, responsable="Logística X")


@pytest.fixture
def media_tmp(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


# --------------------------------------------------------------------------- #
# Compresión pura
# --------------------------------------------------------------------------- #


def test_compresion_bajo_presupuesto():
    grande = _imagen_jpeg(3000, 2000)
    salida, meta = comprimir_a_objetivo(grande)
    assert meta["dentro_de_presupuesto"] is True
    assert len(salida) <= 100_000
    assert max(meta["ancho"], meta["alto"]) <= 1280


# --------------------------------------------------------------------------- #
# Subida + procesamiento
# --------------------------------------------------------------------------- #


def test_subida_devuelve_202_y_encola(autenticar, usuarios, envio, media_tmp):
    api = autenticar(usuarios[Usuario.Rol.CAMPO])
    archivo = SimpleUploadedFile("e.jpg", _imagen_jpeg(), content_type="image/jpeg")
    r = api.post(
        "/api/v1/fotos/",
        {"idempotency_key": str(uuid.uuid4()), "envio": str(envio.id), "imagen": archivo},
        format="multipart",
    )
    assert r.status_code == 202
    assert r.data["estado"] in ("recibida", "procesando", "lista")
    assert Foto.objects.count() == 1


def test_procesar_comprime_y_enlaza(autenticar, usuarios, envio, media_tmp):
    api = autenticar(usuarios[Usuario.Rol.CAMPO])
    archivo = SimpleUploadedFile("e.jpg", _imagen_jpeg(3000, 2000), content_type="image/jpeg")
    r = api.post(
        "/api/v1/fotos/",
        {"idempotency_key": str(uuid.uuid4()), "envio": str(envio.id), "imagen": archivo},
        format="multipart",
    )
    foto = Foto.objects.get(id=r.data["id"])

    procesar_foto(foto.id)  # corre la tarea (en prod la lanza el qcluster)

    foto.refresh_from_db()
    envio.refresh_from_db()
    assert foto.estado == Foto.Estado.LISTA
    assert foto.bytes_comprimida <= 100_000
    assert bool(foto.comprimida)
    assert not foto.original                       # original descartado
    assert envio.foto_confirmacion_ref == foto.comprimida.name


def test_subida_idempotente(autenticar, usuarios, envio, media_tmp):
    api = autenticar(usuarios[Usuario.Rol.CAMPO])
    key = str(uuid.uuid4())

    def subir():
        archivo = SimpleUploadedFile("e.jpg", _imagen_jpeg(), content_type="image/jpeg")
        return api.post(
            "/api/v1/fotos/",
            {"idempotency_key": key, "envio": str(envio.id), "imagen": archivo},
            format="multipart",
        )

    r1 = subir()
    r2 = subir()  # reintento por ACK perdido
    assert r1.status_code == 202
    assert r2.status_code == 200          # devuelve la existente
    assert r1.data["id"] == r2.data["id"]
    assert Foto.objects.count() == 1


def test_subida_enorme_rechazada(autenticar, usuarios, envio, media_tmp, settings):
    settings.FOTO_MAX_SUBIDA_BYTES = 50_000  # bajamos el tope para la prueba
    api = autenticar(usuarios[Usuario.Rol.CAMPO])
    archivo = SimpleUploadedFile("big.jpg", _imagen_jpeg(3000, 2000), content_type="image/jpeg")
    r = api.post(
        "/api/v1/fotos/",
        {"idempotency_key": str(uuid.uuid4()), "envio": str(envio.id), "imagen": archivo},
        format="multipart",
    )
    assert r.status_code == 413
    assert Foto.objects.count() == 0


# --------------------------------------------------------------------------- #
# Permisos
# --------------------------------------------------------------------------- #


def test_lectura_no_sube(autenticar, usuarios, envio, media_tmp):
    api = autenticar(usuarios[Usuario.Rol.LECTURA])
    archivo = SimpleUploadedFile("e.jpg", _imagen_jpeg(), content_type="image/jpeg")
    r = api.post(
        "/api/v1/fotos/",
        {"idempotency_key": str(uuid.uuid4()), "envio": str(envio.id), "imagen": archivo},
        format="multipart",
    )
    assert r.status_code == 403
    assert Foto.objects.count() == 0


def test_anonimo_no_sube(api, envio, media_tmp):
    archivo = SimpleUploadedFile("e.jpg", _imagen_jpeg(), content_type="image/jpeg")
    r = api.post(
        "/api/v1/fotos/",
        {"idempotency_key": str(uuid.uuid4()), "envio": str(envio.id), "imagen": archivo},
        format="multipart",
    )
    assert r.status_code in (401, 403)
