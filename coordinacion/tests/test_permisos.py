"""
Tests de control de acceso por rol (RBAC) - PROMPT_MAESTRO 2.6, 2.7, 6.

Matriz mínima verificada (lectura / campo / coordinador / admin / anonimo):
  GET cualquier ruta ...... si  / si  / si  / si  / no (401)
  POST organizacion ....... no  / no  / no  / si  / no
  POST/PUT catalogo ....... no  / no  / no  / si  / no
  POST necesidad/donacion . no  / si  / si  / si  / no
  POST centro-salud ....... no  / si  / si  / si  / no
  POST sync (push) ........ no  / si  / si  / si  / no
  GET sync (pull) ......... si  / si  / si  / si  / no
  claim necesidad ......... no  / si limitado / si / si / no
  salud ................... publico para todos, incluido anonimo
"""
import pytest

from coordinacion.models import Catalogo, Organizacion, Usuario

pytestmark = pytest.mark.django_db


def test_salud_es_publico(api):
    r = api.get("/api/v1/salud/")
    assert r.status_code == 200


def test_anonimo_no_lee_centros(api):
    r = api.get("/api/v1/centros-salud/")
    assert r.status_code in (401, 403)


def test_anonimo_no_crea_organizacion(api):
    r = api.post(
        "/api/v1/organizaciones/",
        {"nombre": "Anon Corp", "tipo": "ong"},
        format="json",
    )
    assert r.status_code in (401, 403)
    assert not Organizacion.objects.filter(nombre="Anon Corp").exists()


def test_anonimo_no_hace_push_sync(api):
    r = api.post("/api/v1/sync/", {"eventos": []}, format="json")
    assert r.status_code in (401, 403)


def test_lectura_puede_leer(autenticar, usuarios):
    api = autenticar(usuarios[Usuario.Rol.LECTURA])
    assert api.get("/api/v1/centros-salud/").status_code == 200
    assert api.get("/api/v1/necesidades/").status_code == 200


def test_lectura_pull_sync_ok(autenticar, usuarios):
    api = autenticar(usuarios[Usuario.Rol.LECTURA])
    assert api.get("/api/v1/sync/").status_code == 200


def test_lectura_no_escribe_necesidad(autenticar, usuarios, centro, catalogo, organizacion):
    api = autenticar(usuarios[Usuario.Rol.LECTURA])
    r = api.post(
        "/api/v1/necesidades/",
        {
            "centro": str(centro.id),
            "item": str(catalogo.id),
            "cantidad_solicitada": 5,
            "nivel_triage": "2_urgente",
            "reportada_por": str(organizacion.id),
        },
        format="json",
    )
    assert r.status_code == 403


def test_lectura_no_hace_push_sync(autenticar, usuarios):
    api = autenticar(usuarios[Usuario.Rol.LECTURA])
    r = api.post("/api/v1/sync/", {"eventos": []}, format="json")
    assert r.status_code == 403


def test_campo_crea_necesidad(autenticar, usuarios, centro, catalogo, organizacion):
    api = autenticar(usuarios[Usuario.Rol.CAMPO])
    r = api.post(
        "/api/v1/necesidades/",
        {
            "centro": str(centro.id),
            "item": str(catalogo.id),
            "cantidad_solicitada": 5,
            "nivel_triage": "2_urgente",
            "reportada_por": str(organizacion.id),
        },
        format="json",
    )
    assert r.status_code == 201


def test_campo_actualiza_centro(autenticar, usuarios, centro):
    api = autenticar(usuarios[Usuario.Rol.CAMPO])
    r = api.patch(
        f"/api/v1/centros-salud/{centro.id}/",
        {"estado_operativo": "parcial"},
        format="json",
    )
    assert r.status_code == 200


def test_campo_no_crea_organizacion(autenticar, usuarios):
    api = autenticar(usuarios[Usuario.Rol.CAMPO])
    r = api.post(
        "/api/v1/organizaciones/",
        {"nombre": "Nueva ONG", "tipo": "ong"},
        format="json",
    )
    assert r.status_code == 403


def test_campo_no_edita_catalogo(autenticar, usuarios):
    api = autenticar(usuarios[Usuario.Rol.CAMPO])
    r = api.post(
        "/api/v1/catalogos/",
        {"codigo": "X-1", "nombre": "Item", "categoria": "insumo"},
        format="json",
    )
    assert r.status_code == 403


def test_campo_hace_push_sync(autenticar, usuarios):
    api = autenticar(usuarios[Usuario.Rol.CAMPO])
    r = api.post("/api/v1/sync/", {"eventos": []}, format="json")
    assert r.status_code == 200


def test_campo_puede_reclamar_para_su_organizacion(
    autenticar,
    usuarios,
    necesidad,
    donacion,
    organizacion,
):
    api = autenticar(usuarios[Usuario.Rol.CAMPO])
    r = api.post(
        f"/api/v1/necesidades/{necesidad.id}/claim/",
        {
            "donacion_id": str(donacion.id),
            "cantidad_asignada": 5,
            "organizacion_responsable_id": str(organizacion.id),
        },
        format="json",
    )
    assert r.status_code == 201
    assert r.data["estado"] == "confirmada"


def test_campo_no_reclama_para_otra_organizacion(
    autenticar,
    usuarios,
    necesidad,
    donacion,
):
    otra_organizacion = Organizacion.objects.create(
        nombre="Otra organizacion",
        tipo=Organizacion.Tipo.ONG,
    )
    api = autenticar(usuarios[Usuario.Rol.CAMPO])
    r = api.post(
        f"/api/v1/necesidades/{necesidad.id}/claim/",
        {
            "donacion_id": str(donacion.id),
            "cantidad_asignada": 5,
            "organizacion_responsable_id": str(otra_organizacion.id),
        },
        format="json",
    )
    assert r.status_code == 403


def test_coordinador_no_edita_catalogo(autenticar, usuarios):
    api = autenticar(usuarios[Usuario.Rol.COORDINADOR])
    r = api.post(
        "/api/v1/catalogos/",
        {"codigo": "Y-1", "nombre": "Guantes", "categoria": "insumo"},
        format="json",
    )
    assert r.status_code == 403


def test_coordinador_no_crea_organizacion(autenticar, usuarios):
    api = autenticar(usuarios[Usuario.Rol.COORDINADOR])
    r = api.post(
        "/api/v1/organizaciones/",
        {"nombre": "Otra ONG", "tipo": "ong"},
        format="json",
    )
    assert r.status_code == 403


def test_coordinador_puede_reclamar_para_cualquier_organizacion(
    autenticar,
    usuarios,
    necesidad,
    donacion,
):
    otra_organizacion = Organizacion.objects.create(
        nombre="Aliado logistico",
        tipo=Organizacion.Tipo.ONG,
    )
    api = autenticar(usuarios[Usuario.Rol.COORDINADOR])
    r = api.post(
        f"/api/v1/necesidades/{necesidad.id}/claim/",
        {
            "donacion_id": str(donacion.id),
            "cantidad_asignada": 5,
            "organizacion_responsable_id": str(otra_organizacion.id),
        },
        format="json",
    )
    assert r.status_code == 201
    assert r.data["estado"] == "confirmada"


def test_admin_crea_organizacion(autenticar, usuarios):
    api = autenticar(usuarios[Usuario.Rol.ADMIN])
    r = api.post(
        "/api/v1/organizaciones/",
        {"nombre": "Org Admin", "tipo": "ong"},
        format="json",
    )
    assert r.status_code == 201


def test_admin_edita_catalogo(autenticar, usuarios):
    api = autenticar(usuarios[Usuario.Rol.ADMIN])
    r = api.post(
        "/api/v1/catalogos/",
        {"codigo": "ADM-1", "nombre": "Suero", "categoria": "insumo"},
        format="json",
    )
    assert r.status_code == 201
    assert Catalogo.objects.filter(codigo="ADM-1").exists()
