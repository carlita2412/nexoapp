import pytest
from django.core.management import call_command

from coordinacion.models import Catalogo, CentroSalud, Organizacion, Usuario

pytestmark = pytest.mark.django_db


def test_seed_inicial_crea_datos_base_idempotentes():
    call_command("seed_inicial", "--password-inicial", "Temporal-123")
    call_command("seed_inicial", "--password-inicial", "Temporal-123")

    assert Organizacion.objects.count() == 5
    assert Catalogo.objects.count() == 10
    assert CentroSalud.objects.count() == 4
    assert Usuario.objects.count() == 4

    assert Catalogo.objects.filter(codigo="OXI-CONC-5L").exists()
    assert CentroSalud.objects.filter(nombre="Hospital Central de Caracas").exists()


def test_seed_inicial_crea_usuarios_por_rol():
    call_command("seed_inicial", "--password-inicial", "Temporal-123")

    usuarios_por_rol = {
        usuario.rol: usuario for usuario in Usuario.objects.filter(username__startswith="nexo_")
    }

    assert set(usuarios_por_rol) == {
        Usuario.Rol.ADMIN,
        Usuario.Rol.COORDINADOR,
        Usuario.Rol.CAMPO,
        Usuario.Rol.LECTURA,
    }
    assert usuarios_por_rol[Usuario.Rol.ADMIN].is_staff is True
    assert usuarios_por_rol[Usuario.Rol.ADMIN].is_superuser is True
    assert usuarios_por_rol[Usuario.Rol.CAMPO].organizacion is not None
    assert usuarios_por_rol[Usuario.Rol.LECTURA].check_password("Temporal-123")


def test_seed_inicial_sin_usuarios():
    call_command("seed_inicial", "--sin-usuarios")

    assert Organizacion.objects.count() == 5
    assert Catalogo.objects.count() == 10
    assert CentroSalud.objects.count() == 4
    assert Usuario.objects.count() == 0
