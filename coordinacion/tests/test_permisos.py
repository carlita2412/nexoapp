"""
Tests de control de acceso por rol (RBAC) - PROMPT_MAESTRO 2.6, 2.7, 6.

Matriz verificada (lectura / campo / coordinador / admin / anonimo):
  GET cualquier ruta ...... si  / si  / si  / si  / no (401)
  POST organizacion ....... no  / no  / no  / si  / no
  POST/PUT catalogo ....... no  / no  / si  / si  / no
  POST necesidad/donacion . no  / si  / si  / si  / no
  POST centro-salud ....... no  / si  / si  / si  / no
  POST sync (push) ........ no  / si  / si  / si  / no
  GET sync (pull) ......... si  / si  / si  / si  / no
  claim necesidad ......... no  / si  / si  / si  / no
  salud ................... publico para todos, incluido anonimo
"""
import pytest

from coordinacion.models import Organizacion, Usuario

pytestmark = pytest.mark.django_db


# --------------------------------------------------------------------------- #
# Anónimo: cerrado para todo lo sensible, abierto solo a /salud
# --------------------------------------------------------------------------- #


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


# --------------------------------------------------------------------------- #
# Lectura: solo GET, nunca escribe
# --------------------------------------------------------------------------- #


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


# --------------------------------------------------------------------------- #
# Campo: captura en terreno, claim y push; NO administra org ni catálogo
# --------------------------------------------------------------------------- #


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


def test_campo_puede_reclamar(autenticar, usuarios, necesidad, donacion, organizacion):
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


# --------------------------------------------------------------------------- #
# Coordinador: catálogo sí; organización no
# --------------------------------------------------------------------------- #


def test_coordinador_edita_catalogo(autenticar, usuarios):
    api = autenticar(usuarios[Usuario.Rol.COORDINADOR])
    r = api.post(
        "/api/v1/catalogos/",
        {"codigo": "Y-1", "nombre": "Guantes", "categoria": "insumo"},
        format="json",
    )
    assert r.status_code == 201


def test_coordinador_no_crea_organizacion(autenticar, usuarios):
    api = autenticar(usuarios[Usuario.Rol.COORDINADOR])
    r = api.post(
        "/api/v1/organizaciones/",
        {"nombre": "Otra ONG", "tipo": "ong"},
        format="json",
    )
    assert r.status_code == 403


# --------------------------------------------------------------------------- #
# Admin: todo
# --------------------------------------------------------------------------- #


def test_admin_crea_organizacion(autenticar, usuarios):
    api = autenticar(usuarios[Usuario.Rol.ADMIN])
    r = api.post(
        "/api/v1/organizaciones/",
        {"nombre": "Org Admin", "tipo": "ong"},
        format="json",
    )
    assert r.status_code == 201


# --------------------------------------------------------------------------- #
# Login por token: entrega token + rol, y el token autentica
# --------------------------------------------------------------------------- #


def test_login_token_devuelve_rol(api, usuarios, organizacion):
    user = usuarios[Usuario.Rol.COORDINADOR]
    user.set_password("clave-de-prueba-xyz")
    user.save()
    r = api.post(
        "/api/v1/auth/token/",
        {"username": user.username, "password": "clave-de-prueba-xyz"},
        format="json",
    )
    assert r.status_code == 200
    assert r.data["rol"] == "coordinador"
    assert r.data["organizacion"] == str(organizacion.id)
    token = r.data["token"]

    # El token autentica una petición de escritura permitida al coordinador.
    api.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    r2 = api.post(
        "/api/v1/catalogos/",
        {"codigo": "Z-1", "nombre": "Suero", "categoria": "insumo"},
        format="json",
    )
    assert r2.status_code == 201
