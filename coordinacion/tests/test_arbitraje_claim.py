"""
Arbitraje del claim (PROMPT_MAESTRO §5 + regla de oro #4).

- Cobertura parcial: un claim por menos de lo solicitado deja la necesidad PARCIAL.
- Orden por llegada: el primero toma; el segundo solo puede tomar lo que quede.
- No sobre-asignar: un claim que excede lo pendiente se rechaza.
- Donación agotada pasa a 'asignada' y ya no se puede reclamar.
- Item que no corresponde se rechaza.
- Idempotencia: reclamar dos veces con el mismo idempotency_key NO doble-asigna.
"""
import uuid

import pytest

from coordinacion.models import Asignacion, Donacion, Necesidad, Organizacion
from coordinacion.sync.arbitraje import ClaimError, reclamar_necesidad

pytestmark = pytest.mark.django_db


def test_cobertura_parcial(necesidad, donacion, organizacion):
    asig = reclamar_necesidad(
        necesidad_id=necesidad.id,
        donacion_id=donacion.id,
        cantidad_asignada=6,
        organizacion_responsable_id=organizacion.id,
    )
    necesidad.refresh_from_db()
    donacion.refresh_from_db()
    assert asig.estado_claim == Asignacion.EstadoClaim.CONFIRMADA
    assert necesidad.estado == Necesidad.Estado.PARCIAL
    assert necesidad.cantidad_cubierta == 6
    assert donacion.cantidad == 4


def test_cobertura_total_cierra_necesidad(necesidad, donacion, organizacion):
    reclamar_necesidad(
        necesidad_id=necesidad.id,
        donacion_id=donacion.id,
        cantidad_asignada=10,
        organizacion_responsable_id=organizacion.id,
    )
    necesidad.refresh_from_db()
    donacion.refresh_from_db()
    assert necesidad.estado == Necesidad.Estado.CUBIERTA
    assert donacion.estado == Donacion.Estado.ASIGNADA
    assert donacion.cantidad == 0


def test_orden_por_llegada_segundo_toma_el_resto(necesidad, catalogo, organizacion):
    org_b = Organizacion.objects.create(nombre="Org B", tipo="ong")
    don_a = Donacion.objects.create(
        donante=organizacion, item=catalogo, cantidad=6,
        condicion="nuevo", estado="disponible",
    )
    don_b = Donacion.objects.create(
        donante=org_b, item=catalogo, cantidad=6,
        condicion="nuevo", estado="disponible",
    )
    # primero gana 6
    reclamar_necesidad(
        necesidad_id=necesidad.id, donacion_id=don_a.id,
        cantidad_asignada=6, organizacion_responsable_id=organizacion.id,
    )
    # segundo intenta 6 pero solo quedan 4
    with pytest.raises(ClaimError):
        reclamar_necesidad(
            necesidad_id=necesidad.id, donacion_id=don_b.id,
            cantidad_asignada=6, organizacion_responsable_id=org_b.id,
        )
    # segundo ajusta a 4 -> completa
    reclamar_necesidad(
        necesidad_id=necesidad.id, donacion_id=don_b.id,
        cantidad_asignada=4, organizacion_responsable_id=org_b.id,
    )
    necesidad.refresh_from_db()
    assert necesidad.cantidad_cubierta == 10
    assert necesidad.estado == Necesidad.Estado.CUBIERTA


def test_no_sobre_asignar(necesidad, donacion, organizacion):
    with pytest.raises(ClaimError):
        reclamar_necesidad(
            necesidad_id=necesidad.id, donacion_id=donacion.id,
            cantidad_asignada=11, organizacion_responsable_id=organizacion.id,
        )
    necesidad.refresh_from_db()
    assert necesidad.cantidad_cubierta == 0


def test_donacion_agotada_no_se_reclama(necesidad, donacion, organizacion):
    reclamar_necesidad(
        necesidad_id=necesidad.id, donacion_id=donacion.id,
        cantidad_asignada=10, organizacion_responsable_id=organizacion.id,
    )
    # la donación quedó en 'asignada'; un nuevo claim sobre ella falla
    nec2 = Necesidad.objects.create(
        centro=necesidad.centro, item=necesidad.item, cantidad_solicitada=5,
        nivel_triage="3_importante", reportada_por=organizacion,
    )
    with pytest.raises(ClaimError):
        reclamar_necesidad(
            necesidad_id=nec2.id, donacion_id=donacion.id,
            cantidad_asignada=1, organizacion_responsable_id=organizacion.id,
        )


def test_item_que_no_corresponde(necesidad, organizacion):
    from coordinacion.models import Catalogo
    otro = Catalogo.objects.create(codigo="X-9", nombre="Otro", categoria="insumo")
    don = Donacion.objects.create(
        donante=organizacion, item=otro, cantidad=5,
        condicion="nuevo", estado="disponible",
    )
    with pytest.raises(ClaimError):
        reclamar_necesidad(
            necesidad_id=necesidad.id, donacion_id=don.id,
            cantidad_asignada=1, organizacion_responsable_id=organizacion.id,
        )


def test_claim_duplicado_no_doble_asigna(necesidad, donacion, organizacion):
    """Reintento del MISMO claim (ACK perdido) no debe asignar dos veces."""
    key = uuid.uuid4()
    a1 = reclamar_necesidad(
        necesidad_id=necesidad.id, donacion_id=donacion.id,
        cantidad_asignada=5, organizacion_responsable_id=organizacion.id,
        idempotency_key=key,
    )
    a2 = reclamar_necesidad(
        necesidad_id=necesidad.id, donacion_id=donacion.id,
        cantidad_asignada=5, organizacion_responsable_id=organizacion.id,
        idempotency_key=key,
    )
    necesidad.refresh_from_db()
    assert a1.id == a2.id                          # misma asignación
    assert Asignacion.objects.count() == 1         # no se creó otra
    assert necesidad.cantidad_cubierta == 5        # no se sumó dos veces
