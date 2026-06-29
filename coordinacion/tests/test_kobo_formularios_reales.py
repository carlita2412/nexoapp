import uuid

import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from coordinacion.kobo.mapeadores import MapeoKoboError, mapear_donacion, mapear_necesidad
from coordinacion.models import Catalogo, CentroSalud, Donacion, Necesidad, Organizacion


pytestmark = pytest.mark.django_db


def crear_base_kobo():
    organizacion = Organizacion.objects.create(
        id=uuid.uuid4(),
        nombre="Digisalud KoBo",
        tipo=Organizacion.Tipo.ONG,
        verificada=True,
        activa=True,
    )
    item = Catalogo.objects.create(
        id=uuid.uuid4(),
        codigo="MONITOR_SIGNOS",
        nombre="Monitor de signos vitales",
        categoria=Catalogo.Categoria.EQUIPO_MEDICO,
        unidad="unidad",
    )
    centro = CentroSalud.objects.create(
        id=uuid.uuid4(),
        nombre="Hospital Piloto KoBo",
        tipo=CentroSalud.Tipo.HOSPITAL,
        estado_operativo=CentroSalud.EstadoOperativo.OPERATIVO,
        estado="Distrito Capital",
        municipio="Libertador",
        tiene_electricidad=True,
        tiene_agua=True,
        tiene_oxigeno=True,
        tiene_personal_tecnico=True,
    )
    return organizacion, item, centro


def submission_real_necesidad(organizacion, item, centro):
    return {
        "_uuid": "kobo-necesidad-real-001",
        "_submission_time": "2026-06-28T14:30:00Z",
        "centro_id": str(centro.id),
        "item_codigo": item.codigo,
        "cantidad_solicitada": "3",
        "nivel_triage": Necesidad.NivelTriage.CRITICO,
        "reportada_por_id": str(organizacion.id),
        "requiere_electricidad": "si",
        "requiere_oxigeno": "true",
        "requiere_personal_entrenado": "1",
        "requiere_insumos": "no",
    }


def submission_real_necesidad_agrupada(organizacion, item, centro):
    return {
        "_uuid": "kobo-necesidad-real-agrupada-001",
        "_submission_time": "2026-06-28T14:30:00Z",
        "identificacion/centro_id": str(centro.id),
        "identificacion/item_codigo": item.codigo,
        "identificacion/cantidad_solicitada": "3",
        "identificacion/nivel_triage": Necesidad.NivelTriage.CRITICO,
        "identificacion/reportada_por_id": str(organizacion.id),
        "requisitos/requiere_electricidad": "si",
        "requisitos/requiere_oxigeno": "true",
        "requisitos/requiere_personal_entrenado": "1",
        "requisitos/requiere_insumos": "no",
    }


def submission_real_donacion(organizacion, item):
    return {
        "_uuid": "kobo-donacion-real-001",
        "_submission_time": "2026-06-28T14:40:00Z",
        "item_codigo": item.codigo,
        "cantidad": "2",
        "condicion": Donacion.Condicion.USADO_FUNCIONAL,
        "donante_id": str(organizacion.id),
        "geopoint": "10.5000 -66.9167 0 5",
        "ubicacion_texto": "Caracas",
        "certificacion": "Funcional verificado por campo",
    }


def submission_real_donacion_agrupada(organizacion, item):
    return {
        "_uuid": "kobo-donacion-real-agrupada-001",
        "_submission_time": "2026-06-28T14:40:00Z",
        "donacion/item_codigo": item.codigo,
        "donacion/cantidad": "2",
        "donacion/condicion": Donacion.Condicion.USADO_FUNCIONAL,
        "donacion/donante_id": str(organizacion.id),
        "ubicacion/ubicacion_actual": "10.5000 -66.9167 0 5",
        "ubicacion/ubicacion_texto": "Caracas",
        "detalle_tecnico/certificacion": "Funcional verificado por campo",
    }


def test_asset_real_necesidades_mapea_campos_exactos_y_catalogos_csv():
    organizacion, item, centro = crear_base_kobo()

    evento = mapear_necesidad(submission_real_necesidad(organizacion, item, centro))

    assert evento["entity"] == "necesidad"
    assert evento["payload"]["centro"] == str(centro.id)
    assert evento["payload"]["item"] == str(item.id)
    assert evento["payload"]["cantidad_solicitada"] == 3
    assert evento["payload"]["nivel_triage"] == Necesidad.NivelTriage.CRITICO
    assert evento["payload"]["reportada_por"] == str(organizacion.id)
    assert evento["payload"]["requisitos_operacion"] == {
        "requiere_electricidad": True,
        "requiere_oxigeno": True,
        "requiere_personal_entrenado": True,
        "requiere_insumos": False,
    }


def test_asset_real_necesidades_mapea_campos_agrupados_de_xlsform():
    organizacion, item, centro = crear_base_kobo()

    evento = mapear_necesidad(submission_real_necesidad_agrupada(organizacion, item, centro))

    assert evento["entity"] == "necesidad"
    assert evento["payload"]["centro"] == str(centro.id)
    assert evento["payload"]["item"] == str(item.id)
    assert evento["payload"]["cantidad_solicitada"] == 3
    assert evento["payload"]["nivel_triage"] == Necesidad.NivelTriage.CRITICO
    assert evento["payload"]["reportada_por"] == str(organizacion.id)
    assert evento["payload"]["requisitos_operacion"]["requiere_oxigeno"] is True


def test_asset_real_donaciones_mapea_geopoint_y_catalogos_csv():
    organizacion, item, _centro = crear_base_kobo()

    evento = mapear_donacion(submission_real_donacion(organizacion, item))

    punto = evento["payload"]["ubicacion_actual"]
    assert evento["entity"] == "donacion"
    assert evento["payload"]["donante"] == str(organizacion.id)
    assert evento["payload"]["item"] == str(item.id)
    assert evento["payload"]["cantidad"] == 2
    assert evento["payload"]["condicion"] == Donacion.Condicion.USADO_FUNCIONAL
    assert round(punto.y, 4) == 10.5
    assert round(punto.x, 4) == -66.9167


def test_asset_real_donaciones_mapea_campos_agrupados_de_xlsform():
    organizacion, item, _centro = crear_base_kobo()

    evento = mapear_donacion(submission_real_donacion_agrupada(organizacion, item))

    punto = evento["payload"]["ubicacion_actual"]
    assert evento["entity"] == "donacion"
    assert evento["payload"]["donante"] == str(organizacion.id)
    assert evento["payload"]["item"] == str(item.id)
    assert evento["payload"]["cantidad"] == 2
    assert round(punto.y, 4) == 10.5
    assert round(punto.x, 4) == -66.9167


def test_necesidad_rechaza_nombre_de_campo_incorrecto():
    organizacion, item, centro = crear_base_kobo()
    submission = submission_real_necesidad(organizacion, item, centro)
    submission.pop("centro_id")
    submission["centro_nombre"] = centro.nombre

    with pytest.raises(MapeoKoboError, match="centro_id"):
        mapear_necesidad(submission)


def test_donacion_rechaza_coordenadas_invalidas():
    organizacion, item, _centro = crear_base_kobo()
    submission = submission_real_donacion(organizacion, item)
    submission["geopoint"] = "sin coordenadas"

    with pytest.raises(MapeoKoboError, match="ubicacion_actual"):
        mapear_donacion(submission)


def test_donacion_rechaza_catalogo_no_exportado_en_csv():
    organizacion, item, _centro = crear_base_kobo()
    submission = submission_real_donacion(organizacion, item)
    submission["item_codigo"] = "CODIGO_NO_EXPORTADO"

    with pytest.raises(MapeoKoboError, match="Catálogo no existe"):
        mapear_donacion(submission)


@override_settings(KOBO_WEBHOOK_TOKEN="token-secreto-kobo")
def test_webhook_kobo_rechaza_token_invalido():
    client = APIClient()
    url = reverse("kobo-webhook", kwargs={"tipo": "donacion"})

    response = client.post(url, {}, format="json", HTTP_X_KOBO_TOKEN="incorrecto")

    assert response.status_code == 403
    assert response.json()["detail"] == "Token de webhook inválido."


@override_settings(KOBO_WEBHOOK_TOKEN="token-secreto-kobo")
def test_webhook_kobo_acepta_token_y_procesa_submission_real():
    organizacion, item, _centro = crear_base_kobo()
    client = APIClient()
    url = reverse("kobo-webhook", kwargs={"tipo": "donacion"})

    response = client.post(
        url,
        submission_real_donacion(organizacion, item),
        format="json",
        HTTP_X_KOBO_TOKEN="token-secreto-kobo",
    )

    assert response.status_code == 201
    assert response.json()["estado"] == "ok"
    assert Donacion.objects.filter(item=item, donante=organizacion, cantidad=2).exists()
