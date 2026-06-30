import uuid

import pytest

from coordinacion.kobo.mapeadores import mapear_submission
from coordinacion.models import Catalogo, CentroSalud, Organizacion


@pytest.mark.django_db
def test_mapear_necesidad_kobo_es_idempotente():
    centro = CentroSalud.objects.create(
        nombre="Hospital Central",
        tipo=CentroSalud.Tipo.HOSPITAL,
        estado="Miranda",
        municipio="Sucre",
    )
    item = Catalogo.objects.create(
        codigo="MONITOR-SV",
        nombre="Monitor de signos vitales",
        categoria=Catalogo.Categoria.EQUIPO_MEDICO,
    )
    org = Organizacion.objects.create(
        nombre="Digisalud",
        tipo=Organizacion.Tipo.ONG,
    )
    submission = {
        "_uuid": "abc-123",
        "_submission_time": "2026-06-27T12:00:00-04:00",
        "centro_id": str(centro.id),
        "item_codigo": item.codigo,
        "reportada_por_id": str(org.id),
        "cantidad_solicitada": "2",
        "nivel_triage": "1_critico",
        "requiere_electricidad": "si",
        "requiere_oxigeno": "no",
    }

    evento_1 = mapear_submission("necesidad", submission)
    evento_2 = mapear_submission("necesidad", submission)

    assert evento_1 == evento_2
    uuid.UUID(evento_1["idempotency_key"])
    assert evento_1["entity"] == "necesidad"
    assert evento_1["payload"]["cantidad_solicitada"] == 2
    assert evento_1["payload"]["requisitos_operacion"]["requiere_electricidad"] is True


@pytest.mark.django_db
def test_mapear_necesidad_kobo_con_submission_time_sin_timezone():
    centro = CentroSalud.objects.create(
        nombre="Hospital Central",
        tipo=CentroSalud.Tipo.HOSPITAL,
        estado="Miranda",
        municipio="Sucre",
    )
    item = Catalogo.objects.create(
        codigo="MONITOR-SV",
        nombre="Monitor de signos vitales",
        categoria=Catalogo.Categoria.EQUIPO_MEDICO,
    )
    org = Organizacion.objects.create(
        nombre="Digisalud",
        tipo=Organizacion.Tipo.ONG,
    )
    submission = {
        "_uuid": "abc-456",
        "_submission_time": "2026-06-27T12:00:00",
        "centro_id": str(centro.id),
        "item_codigo": item.codigo,
        "reportada_por_id": str(org.id),
        "cantidad_solicitada": "1",
        "nivel_triage": "1_critico",
    }

    evento = mapear_submission("necesidad", submission)

    assert evento["client_timestamp"] == "2026-06-27T12:00:00+00:00"


@pytest.mark.django_db
def test_mapear_donacion_kobo_crea_evento_disponible():
    item = Catalogo.objects.create(
        codigo="GUANTES-M",
        nombre="Guantes talla M",
        categoria=Catalogo.Categoria.INSUMO,
    )
    donante = Organizacion.objects.create(
        nombre="Donante privado",
        tipo=Organizacion.Tipo.DONANTE_PRIVADO,
    )
    submission = {
        "_uuid": "don-456",
        "_submission_time": "2026-06-27T13:00:00-04:00",
        "item_codigo": item.codigo,
        "donante_id": str(donante.id),
        "cantidad": "50",
        "condicion": "nuevo",
        "ubicacion_texto": "Caracas",
    }

    evento = mapear_submission("donacion", submission)

    assert evento["entity"] == "donacion"
    assert evento["payload"]["item"] == str(item.id)
    assert evento["payload"]["donante"] == str(donante.id)
    assert evento["payload"]["cantidad"] == 50
    assert evento["payload"]["estado"] == "disponible"
