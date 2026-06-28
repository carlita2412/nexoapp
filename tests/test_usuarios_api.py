import uuid

import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from coordinacion.models import Catalogo, CentroSalud, Necesidad, Organizacion, Usuario


@pytest.fixture
def organizacion():
    return Organizacion.objects.create(
        nombre="Digisalud",
        tipo=Organizacion.Tipo.ONG,
        verificada=True,
        activa=True,
    )


@pytest.fixture
def usuario_campo(organizacion):
    usuario = Usuario.objects.create_user(
        username="campo",
        password="clave-segura-123",
        rol=Usuario.Rol.CAMPO,
        organizacion=organizacion,
    )
    return usuario


@pytest.fixture
def usuario_lectura(organizacion):
    usuario = Usuario.objects.create_user(
        username="lectura",
        password="clave-segura-123",
        rol=Usuario.Rol.LECTURA,
        organizacion=organizacion,
    )
    return usuario


@pytest.fixture
def usuario_coordinador(organizacion):
    usuario = Usuario.objects.create_user(
        username="coordinador",
        password="clave-segura-123",
        rol=Usuario.Rol.COORDINADOR,
        organizacion=organizacion,
    )
    return usuario


@pytest.fixture
def datos_base(organizacion):
    centro = CentroSalud.objects.create(
        nombre="Ambulatorio El Hatillo",
        tipo=CentroSalud.Tipo.AMBULATORIO,
        estado="Miranda",
        municipio="El Hatillo",
        tiene_electricidad=True,
        tiene_agua=True,
        tiene_oxigeno=False,
        tiene_personal_tecnico=True,
    )
    item = Catalogo.objects.create(
        codigo="MONITOR-SV",
        nombre="Monitor de signos vitales",
        categoria=Catalogo.Categoria.EQUIPO_MEDICO,
        unidad="unidad",
    )
    return {"centro": centro, "item": item, "organizacion": organizacion}


def autenticar(usuario):
    cliente = APIClient()
    token, _ = Token.objects.get_or_create(user=usuario)
    cliente.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return cliente


@pytest.mark.django_db
def test_login_devuelve_token_rol_y_organizacion(usuario_campo, organizacion):
    cliente = APIClient()

    respuesta = cliente.post(
        "/api/v1/auth/token/",
        {"username": "campo", "password": "clave-segura-123"},
        format="json",
    )

    assert respuesta.status_code == 200
    assert respuesta.data["token"]
    assert respuesta.data["usuario"] == "campo"
    assert respuesta.data["rol"] == Usuario.Rol.CAMPO
    assert respuesta.data["organizacion"] == str(organizacion.id)


@pytest.mark.django_db
def test_usuario_anonimo_no_puede_ver_catalogo():
    cliente = APIClient()

    respuesta = cliente.get("/api/v1/catalogos/")

    assert respuesta.status_code in {401, 403}


@pytest.mark.django_db
def test_usuario_lectura_puede_leer_pero_no_crear_catalogo(usuario_lectura):
    cliente = autenticar(usuario_lectura)

    lectura = cliente.get("/api/v1/catalogos/")
    escritura = cliente.post(
        "/api/v1/catalogos/",
        {
            "id": str(uuid.uuid4()),
            "codigo": "OXIMETRO",
            "nombre": "Oxímetro",
            "categoria": Catalogo.Categoria.EQUIPO_MEDICO,
            "unidad": "unidad",
        },
        format="json",
    )

    assert lectura.status_code == 200
    assert escritura.status_code == 403


@pytest.mark.django_db
def test_usuario_campo_puede_crear_necesidad_desde_aplicacion(usuario_campo, datos_base):
    cliente = autenticar(usuario_campo)

    respuesta = cliente.post(
        "/api/v1/necesidades/",
        {
            "id": str(uuid.uuid4()),
            "centro": str(datos_base["centro"].id),
            "item": str(datos_base["item"].id),
            "cantidad_solicitada": 2,
            "cantidad_cubierta": 0,
            "nivel_triage": Necesidad.NivelTriage.CRITICO,
            "requisitos_operacion": {
                "requiere_electricidad": True,
                "requiere_oxigeno": False,
                "requiere_personal_entrenado": True,
            },
            "estado": Necesidad.Estado.ABIERTA,
            "reportada_por": str(datos_base["organizacion"].id),
        },
        format="json",
    )

    assert respuesta.status_code == 201
    assert Necesidad.objects.count() == 1
    necesidad = Necesidad.objects.get()
    assert necesidad.cantidad_solicitada == 2
    assert necesidad.nivel_triage == Necesidad.NivelTriage.CRITICO


@pytest.mark.django_db
def test_usuario_coordinador_puede_crear_catalogo(usuario_coordinador):
    cliente = autenticar(usuario_coordinador)

    respuesta = cliente.post(
        "/api/v1/catalogos/",
        {
            "id": str(uuid.uuid4()),
            "codigo": "GLUCOMETRO",
            "nombre": "Glucómetro",
            "categoria": Catalogo.Categoria.EQUIPO_MEDICO,
            "unidad": "unidad",
        },
        format="json",
    )

    assert respuesta.status_code == 201
    assert Catalogo.objects.filter(codigo="GLUCOMETRO").exists()


@pytest.mark.django_db
def test_usuario_lectura_no_puede_hacer_push_sync(usuario_lectura):
    cliente = autenticar(usuario_lectura)

    respuesta = cliente.post(
        "/api/v1/sync/",
        {"eventos": []},
        format="json",
    )

    assert respuesta.status_code == 403


@pytest.mark.django_db
def test_usuario_campo_puede_hacer_push_sync(usuario_campo):
    cliente = autenticar(usuario_campo)

    respuesta = cliente.post(
        "/api/v1/sync/",
        {"eventos": []},
        format="json",
    )

    assert respuesta.status_code == 200
    assert "cursor" in respuesta.data
    assert respuesta.data["resultados"] == []
