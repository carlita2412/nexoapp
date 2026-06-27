import uuid

import pytest
from rest_framework.test import APIClient

from coordinacion.models import (
    Catalogo,
    CentroSalud,
    Donacion,
    Necesidad,
    Organizacion,
    Usuario,
)


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def organizacion(db):
    return Organizacion.objects.create(nombre="Cruz Local", tipo=Organizacion.Tipo.ONG)


def _crear_usuario(rol, organizacion):
    user = Usuario.objects.create_user(
        username=f"u_{rol}_{uuid.uuid4().hex[:6]}",
        password="clave-segura-123",
        rol=rol,
        organizacion=organizacion,
    )
    return user


@pytest.fixture
def usuarios(db, organizacion):
    """Un usuario por cada rol del dominio."""
    return {
        rol: _crear_usuario(rol, organizacion)
        for rol in (
            Usuario.Rol.ADMIN,
            Usuario.Rol.COORDINADOR,
            Usuario.Rol.CAMPO,
            Usuario.Rol.LECTURA,
        )
    }


@pytest.fixture
def autenticar(api):
    """Devuelve un cliente autenticado como el usuario dado (force_authenticate)."""

    def _login(usuario):
        api.force_authenticate(user=usuario)
        return api

    return _login


@pytest.fixture
def catalogo(db):
    return Catalogo.objects.create(
        codigo="OXI-001",
        nombre="Concentrador de oxígeno",
        categoria=Catalogo.Categoria.EQUIPO_MEDICO,
    )


@pytest.fixture
def centro(db):
    return CentroSalud.objects.create(
        nombre="Hospital Centro",
        tipo=CentroSalud.Tipo.HOSPITAL,
        estado="Vargas",
        municipio="Vargas",
        tiene_electricidad=True,
        tiene_oxigeno=True,
    )


@pytest.fixture
def necesidad(db, centro, catalogo, organizacion):
    return Necesidad.objects.create(
        centro=centro,
        item=catalogo,
        cantidad_solicitada=10,
        nivel_triage=Necesidad.NivelTriage.URGENTE,
        reportada_por=organizacion,
    )


@pytest.fixture
def donacion(db, catalogo, organizacion):
    return Donacion.objects.create(
        donante=organizacion,
        item=catalogo,
        cantidad=10,
        condicion=Donacion.Condicion.NUEVO,
        estado=Donacion.Estado.DISPONIBLE,
    )
