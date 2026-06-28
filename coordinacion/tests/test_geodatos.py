import uuid

import pytest
from django.contrib.gis.geos import Point

from coordinacion.geo import normalizar_point, point_a_dict
from coordinacion.models import CentroSalud, Donacion, Envio
from coordinacion.serializers import CentroSaludSerializer, DonacionSerializer
from coordinacion.sync.procesador import procesar_evento_sync, serializar_objeto_sync

pytestmark = pytest.mark.django_db


def test_normalizar_geopoint_kobo_lat_lon():
    punto = normalizar_point("10.5000 -66.9000 0 5")

    assert isinstance(punto, Point)
    assert punto.srid == 4326
    assert punto.y == pytest.approx(10.5)
    assert punto.x == pytest.approx(-66.9)


def test_normalizar_geojson_lon_lat():
    punto = normalizar_point({"type": "Point", "coordinates": [-66.9, 10.5]})

    assert punto.y == pytest.approx(10.5)
    assert punto.x == pytest.approx(-66.9)


def test_centro_salud_serializer_acepta_point_geojson():
    serializer = CentroSaludSerializer(
        data={
            "nombre": "Hospital Georreferenciado",
            "tipo": CentroSalud.Tipo.HOSPITAL,
            "estado_operativo": CentroSalud.EstadoOperativo.OPERATIVO,
            "geolocalizacion": {"type": "Point", "coordinates": [-66.9, 10.5]},
            "estado": "Distrito Capital",
            "municipio": "Libertador",
            "tiene_electricidad": True,
            "tiene_agua": True,
            "tiene_oxigeno": True,
            "tiene_personal_tecnico": True,
        }
    )

    assert serializer.is_valid(), serializer.errors
    centro = serializer.save()

    assert centro.geolocalizacion.x == pytest.approx(-66.9)
    assert serializer.data["geolocalizacion"]["coordinates"] == [-66.9, 10.5]


def test_sync_crea_donacion_con_pointfield(catalogo, organizacion):
    entity_id = uuid.uuid4()
    resultado = procesar_evento_sync(
        {
            "idempotency_key": uuid.uuid4(),
            "entity": "donacion",
            "payload": {
                "id": str(entity_id),
                "donante": str(organizacion.id),
                "item": str(catalogo.id),
                "cantidad": 2,
                "condicion": Donacion.Condicion.NUEVO,
                "ubicacion_actual": "10.5 -66.9 0 5",
                "ubicacion_texto": "Depósito Caracas",
                "estado": Donacion.Estado.DISPONIBLE,
                "version": 1,
            },
        }
    )

    assert resultado["estado"] == "ok"
    donacion = Donacion.objects.get(id=entity_id)
    assert donacion.ubicacion_actual.x == pytest.approx(-66.9)
    assert donacion.ubicacion_actual.y == pytest.approx(10.5)


def test_serializacion_sync_devuelve_geojson(centro):
    centro.geolocalizacion = normalizar_point("10.5 -66.9")
    centro.save(update_fields=["geolocalizacion"])

    data = serializar_objeto_sync(centro)

    assert data["geolocalizacion"] == {
        "type": "Point",
        "coordinates": [-66.9, 10.5],
        "srid": 4326,
    }


def test_envio_guarda_geolocalizacion_entrega_pointfield(necesidad, donacion, organizacion):
    from coordinacion.models import Asignacion
    from django.utils import timezone

    asignacion = Asignacion.objects.create(
        necesidad=necesidad,
        donacion=donacion,
        cantidad_asignada=1,
        organizacion_responsable=organizacion,
        claim_ts_cliente=timezone.now(),
        estado_claim=Asignacion.EstadoClaim.CONFIRMADA,
    )
    envio = Envio.objects.create(
        asignacion=asignacion,
        responsable="Equipo campo",
        geolocalizacion_entrega=normalizar_point("10.51 -66.91"),
        estado=Envio.Estado.ENTREGADO,
    )

    assert point_a_dict(envio.geolocalizacion_entrega)["coordinates"] == [-66.91, 10.51]


def test_donacion_serializer_rechaza_coordenadas_invalidas(catalogo, organizacion):
    serializer = DonacionSerializer(
        data={
            "donante": str(organizacion.id),
            "item": str(catalogo.id),
            "cantidad": 1,
            "condicion": Donacion.Condicion.NUEVO,
            "ubicacion_actual": "sin coordenadas",
            "estado": Donacion.Estado.DISPONIBLE,
        }
    )

    assert serializer.is_valid() is False
    assert "ubicacion_actual" in serializer.errors
