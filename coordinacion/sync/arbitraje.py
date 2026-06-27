from django.db import transaction
from django.utils import timezone

from coordinacion.models import Asignacion, Donacion, Necesidad, Organizacion


class ClaimError(Exception):
    pass


@transaction.atomic
def reclamar_necesidad(
    *,
    necesidad_id,
    donacion_id,
    cantidad_asignada,
    organizacion_responsable_id,
) -> Asignacion:
    necesidad = Necesidad.objects.select_for_update().get(id=necesidad_id)
    donacion = Donacion.objects.select_for_update().get(id=donacion_id)
    organizacion = Organizacion.objects.get(id=organizacion_responsable_id)

    if necesidad.estado not in [Necesidad.Estado.ABIERTA, Necesidad.Estado.PARCIAL]:
        raise ClaimError("La necesidad no está abierta ni parcial.")

    if donacion.estado != Donacion.Estado.DISPONIBLE:
        raise ClaimError("La donación no está disponible.")

    if donacion.item_id != necesidad.item_id:
        raise ClaimError("La donación no corresponde al item solicitado.")

    if cantidad_asignada <= 0:
        raise ClaimError("La cantidad asignada debe ser mayor que cero.")

    cantidad_pendiente = necesidad.cantidad_solicitada - necesidad.cantidad_cubierta

    if cantidad_pendiente <= 0:
        necesidad.estado = Necesidad.Estado.CUBIERTA
        necesidad.save(update_fields=["estado", "updated_at"])
        raise ClaimError("La necesidad ya está cubierta.")

    if cantidad_asignada > cantidad_pendiente:
        raise ClaimError(
            f"La cantidad asignada excede lo pendiente. Pendiente: {cantidad_pendiente}."
        )

    if cantidad_asignada > donacion.cantidad:
        raise ClaimError(
            f"La cantidad asignada excede la cantidad disponible de la donación. Disponible: {donacion.cantidad}."
        )

    ahora = timezone.now()

    asignacion = Asignacion.objects.create(
        necesidad=necesidad,
        donacion=donacion,
        cantidad_asignada=cantidad_asignada,
        organizacion_responsable=organizacion,
        estado_claim=Asignacion.EstadoClaim.CONFIRMADA,
        claim_ts_cliente=ahora,
        claim_ts_servidor=ahora,
        estado_logistico=Asignacion.EstadoLogistico.PENDIENTE,
    )

    necesidad.cantidad_cubierta += cantidad_asignada

    if necesidad.cantidad_cubierta >= necesidad.cantidad_solicitada:
        necesidad.estado = Necesidad.Estado.CUBIERTA
    elif necesidad.cantidad_cubierta > 0:
        necesidad.estado = Necesidad.Estado.PARCIAL

    necesidad.version += 1
    necesidad.save(
        update_fields=[
            "cantidad_cubierta",
            "estado",
            "version",
            "updated_at",
        ]
    )

    donacion.cantidad -= cantidad_asignada

    if donacion.cantidad <= 0:
        donacion.estado = Donacion.Estado.ASIGNADA

    donacion.version += 1
    donacion.save(
        update_fields=[
            "cantidad",
            "estado",
            "version",
            "updated_at",
        ]
    )

    return asignacion