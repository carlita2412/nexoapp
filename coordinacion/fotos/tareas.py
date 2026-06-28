"""
Procesamiento asíncrono de fotos de entrega (django-q2).

Flujo: recibida -> procesando -> (lista | error).
Al quedar lista, fija `Envio.foto_confirmacion_ref` con la clave del blob
comprimido (§4) y borra el original (§2 presupuesto, §7 privacidad).
"""
from django.conf import settings
from django.core.files.base import ContentFile

from coordinacion.fotos.compresion import comprimir_a_objetivo
from coordinacion.models import Foto


def procesar_foto(foto_id) -> str:
    foto = Foto.objects.select_related("envio").get(id=foto_id)

    if foto.estado == Foto.Estado.LISTA:
        return "ya_lista"  # idempotente ante reintentos del worker

    foto.estado = Foto.Estado.PROCESANDO
    foto.save(update_fields=["estado", "updated_at"])

    try:
        datos = foto.original.read()
        foto.bytes_original = len(datos)

        objetivo = getattr(settings, "FOTO_OBJETIVO_BYTES", 100_000)
        comprimida, meta = comprimir_a_objetivo(datos, objetivo_bytes=objetivo)

        nombre = f"{foto.id}.jpg"
        foto.comprimida.save(nombre, ContentFile(comprimida), save=False)
        foto.bytes_comprimida = meta["bytes"]
        foto.estado = Foto.Estado.LISTA
        foto.error_detalle = ""
        foto.save(
            update_fields=[
                "comprimida",
                "bytes_original",
                "bytes_comprimida",
                "estado",
                "error_detalle",
                "updated_at",
            ]
        )

        # enlazar con el envío y descartar el original
        envio = foto.envio
        envio.foto_confirmacion_ref = foto.comprimida.name
        envio.save(update_fields=["foto_confirmacion_ref", "updated_at"])

        foto.original.delete(save=False)
        foto.original = None
        foto.save(update_fields=["original", "updated_at"])

        return "lista"

    except Exception as exc:  # noqa: BLE001 - registramos cualquier fallo
        foto.estado = Foto.Estado.ERROR
        foto.error_detalle = str(exc)[:500]
        foto.save(update_fields=["estado", "error_detalle", "updated_at"])
        return "error"


def encolar_procesamiento(foto_id) -> None:
    """Encola la compresión. En modo sync (tests) corre en línea."""
    from django_q.tasks import async_task

    async_task("coordinacion.fotos.tareas.procesar_foto", foto_id)
