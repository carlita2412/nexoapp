"""
Pull por deltas de /sync y motor de matching (PROMPT_MAESTRO §3, §5).

- Pull sin cursor devuelve todo; con cursor solo lo cambiado después de él.
- Matching: compatible cuando el centro cumple los requisitos de operación;
  incompatible cuando falta una capacidad, el item no coincide, o la donación
  requiere reparación.
"""
import time

import pytest
from django.utils import timezone

from coordinacion.models import Catalogo, CentroSalud, Donacion, Necesidad, Organizacion
from coordinacion.sync.matching import (
    centro_cumple_requisitos,
    evaluar_donacion_para_necesidad,
    obtener_candidatos_para_necesidad,
)
from coordinacion.sync.procesador import obtener_deltas

pytestmark = pytest.mark.django_db


# --------------------------------------------------------------------------- #
# Pull por deltas
# --------------------------------------------------------------------------- #


def test_pull_sin_cursor_devuelve_todo(organizacion, catalogo):
    data = obtener_deltas(desde=None)
    ids_orgs = [o["id"] for o in data["deltas"]["organizaciones"]]
    assert str(organizacion.id) in ids_orgs
    assert "cursor" in data


def test_pull_con_cursor_solo_lo_nuevo(catalogo):
    # primera tanda
    Organizacion.objects.create(nombre="Org Vieja", tipo="ong")
    time.sleep(0.01)
    corte = timezone.now()
    time.sleep(0.01)
    # segunda tanda, posterior al corte
    nueva = Organizacion.objects.create(nombre="Org Nueva", tipo="ong")

    data = obtener_deltas(desde=corte)
    ids = [o["id"] for o in data["deltas"]["organizaciones"]]

    assert str(nueva.id) in ids
    assert all(
        Organizacion.objects.get(id=i).nombre != "Org Vieja" for i in ids
    )


def test_delta_incluye_version(organizacion):
    data = obtener_deltas(desde=None)
    fila = next(
        o for o in data["deltas"]["organizaciones"] if o["id"] == str(organizacion.id)
    )
    assert fila["version"] == organizacion.version
    assert "updated_at" in fila


# --------------------------------------------------------------------------- #
# Matching
# --------------------------------------------------------------------------- #


def test_centro_cumple_requisitos(necesidad):
    # el centro de la fixture tiene electricidad y oxígeno
    necesidad.requisitos_operacion = {"requiere_electricidad": True, "requiere_oxigeno": True}
    ok, _ = centro_cumple_requisitos(necesidad)
    assert ok is True


def test_centro_no_cumple_requisitos(necesidad):
    necesidad.requisitos_operacion = {"requiere_agua": True}  # el centro NO tiene agua
    ok, motivo = centro_cumple_requisitos(necesidad)
    assert ok is False
    assert "agua" in motivo.lower()


def test_donacion_compatible(necesidad, donacion):
    r = evaluar_donacion_para_necesidad(necesidad, donacion)
    assert r.compatible is True
    assert r.puntaje > 0


def test_donacion_item_distinto_incompatible(necesidad, organizacion):
    otro_item = Catalogo.objects.create(
        codigo="GUA-001", nombre="Guantes", categoria="insumo"
    )
    don = Donacion.objects.create(
        donante=organizacion, item=otro_item, cantidad=5,
        condicion="nuevo", estado="disponible",
    )
    r = evaluar_donacion_para_necesidad(necesidad, don)
    assert r.compatible is False


def test_donacion_requiere_reparacion_excluida(necesidad, catalogo, organizacion):
    don = Donacion.objects.create(
        donante=organizacion, item=catalogo, cantidad=5,
        condicion="requiere_reparacion", estado="disponible",
    )
    r = evaluar_donacion_para_necesidad(necesidad, don)
    assert r.compatible is False
    assert "reparación" in r.motivo.lower()


def test_candidatos_excluye_centro_incompatible(necesidad, catalogo, organizacion):
    # la necesidad exige agua, pero el centro no la tiene -> sin candidatos
    necesidad.requisitos_operacion = {"requiere_agua": True}
    necesidad.save(update_fields=["requisitos_operacion"])
    Donacion.objects.create(
        donante=organizacion, item=catalogo, cantidad=5,
        condicion="nuevo", estado="disponible",
    )
    candidatos = obtener_candidatos_para_necesidad(necesidad)
    assert candidatos == []


def test_candidatos_ordenados_por_puntaje(necesidad, catalogo, organizacion):
    # nuevo (mejor) vs usado_funcional -> el nuevo debe ir primero
    Donacion.objects.create(
        donante=organizacion, item=catalogo, cantidad=20,
        condicion="usado_funcional", estado="disponible",
    )
    Donacion.objects.create(
        donante=organizacion, item=catalogo, cantidad=20,
        condicion="nuevo", estado="disponible",
    )
    candidatos = obtener_candidatos_para_necesidad(necesidad)
    assert len(candidatos) == 2
    assert candidatos[0].puntaje >= candidatos[1].puntaje
    assert candidatos[0].donacion.condicion == "nuevo"
