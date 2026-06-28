from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from django.contrib.auth.hashers import make_password

from coordinacion.models import Catalogo, CentroSalud, Organizacion, Usuario

NAMESPACE_SEED = uuid.UUID("8b710f8e-1bf6-4c42-9a5c-c8ed8f2a7d11")


def uuid_seed(clave: str) -> uuid.UUID:
    """Genera UUID estable para que el seed sea idempotente entre ambientes."""

    return uuid.uuid5(NAMESPACE_SEED, clave)


@dataclass(frozen=True)
class UsuarioSeed:
    username: str
    rol: str
    organizacion_clave: str
    email: str
    first_name: str
    last_name: str = "Nexo"
    is_staff: bool = False
    is_superuser: bool = False


ORGANIZACIONES: tuple[dict[str, Any], ...] = (
    {
        "clave": "digisalud",
        "nombre": "Digisalud",
        "tipo": Organizacion.Tipo.ONG,
        "contacto": "coordinacion@digisalud.org",
        "verificada": True,
        "activa": True,
    },
    {
        "clave": "alianza_medica_caracas",
        "nombre": "Alianza Medica Caracas",
        "tipo": Organizacion.Tipo.ONG,
        "contacto": "operaciones@nexo.local",
        "verificada": True,
        "activa": True,
    },
    {
        "clave": "red_centros_salud",
        "nombre": "Red de Centros de Salud Aliados",
        "tipo": Organizacion.Tipo.CENTRO_SALUD,
        "contacto": "centros@nexo.local",
        "verificada": True,
        "activa": True,
    },
    {
        "clave": "voluntarios_campo",
        "nombre": "Voluntarios de Campo Nexo",
        "tipo": Organizacion.Tipo.VOLUNTARIO,
        "contacto": "campo@nexo.local",
        "verificada": True,
        "activa": True,
    },
    {
        "clave": "donantes_privados",
        "nombre": "Donantes Privados Verificados",
        "tipo": Organizacion.Tipo.DONANTE_PRIVADO,
        "contacto": "donantes@nexo.local",
        "verificada": True,
        "activa": True,
    },
)

CATALOGOS: tuple[dict[str, Any], ...] = (
    {
        "codigo": "OXI-CONC-5L",
        "nombre": "Concentrador de oxigeno 5 LPM",
        "categoria": Catalogo.Categoria.EQUIPO_MEDICO,
        "unidad": "unidad",
    },
    {
        "codigo": "OXI-CIL-10M3",
        "nombre": "Cilindro de oxigeno 10 m3",
        "categoria": Catalogo.Categoria.EQUIPO_MEDICO,
        "unidad": "unidad",
    },
    {
        "codigo": "MON-SV-BASICO",
        "nombre": "Monitor de signos vitales basico",
        "categoria": Catalogo.Categoria.EQUIPO_MEDICO,
        "unidad": "unidad",
    },
    {
        "codigo": "TENS-ADULTO",
        "nombre": "Tensiometro adulto",
        "categoria": Catalogo.Categoria.EQUIPO_MEDICO,
        "unidad": "unidad",
    },
    {
        "codigo": "GLUC-BASICO",
        "nombre": "Glucometro con tiras",
        "categoria": Catalogo.Categoria.EQUIPO_MEDICO,
        "unidad": "kit",
    },
    {
        "codigo": "SUERO-FIS-500ML",
        "nombre": "Solucion fisiologica 0.9% 500 ml",
        "categoria": Catalogo.Categoria.INSUMO,
        "unidad": "bolsa",
    },
    {
        "codigo": "GUANTE-NIT-M",
        "nombre": "Guantes de nitrilo talla M",
        "categoria": Catalogo.Categoria.INSUMO,
        "unidad": "caja",
    },
    {
        "codigo": "MASC-N95",
        "nombre": "Mascarilla N95",
        "categoria": Catalogo.Categoria.INSUMO,
        "unidad": "unidad",
    },
    {
        "codigo": "KIT-CURA",
        "nombre": "Kit de curas basico",
        "categoria": Catalogo.Categoria.INSUMO,
        "unidad": "kit",
    },
    {
        "codigo": "GEN-PORT-5KVA",
        "nombre": "Generador electrico portatil 5 kVA",
        "categoria": Catalogo.Categoria.INFRAESTRUCTURA,
        "unidad": "unidad",
    },
)

CENTROS_SALUD: tuple[dict[str, Any], ...] = (
    {
        "clave": "hospital_central_caracas",
        "nombre": "Hospital Central de Caracas",
        "tipo": CentroSalud.Tipo.HOSPITAL,
        "estado_operativo": CentroSalud.EstadoOperativo.PARCIAL,
        "geolocalizacion": "10.5000,-66.9167",
        "estado": "Distrito Capital",
        "municipio": "Libertador",
        "tiene_electricidad": True,
        "tiene_agua": True,
        "tiene_oxigeno": True,
        "tiene_personal_tecnico": True,
        "contacto_responsable": "Coordinacion hospitalaria",
    },
    {
        "clave": "ambulatorio_petare",
        "nombre": "Ambulatorio Petare",
        "tipo": CentroSalud.Tipo.AMBULATORIO,
        "estado_operativo": CentroSalud.EstadoOperativo.PARCIAL,
        "geolocalizacion": "10.4760,-66.8030",
        "estado": "Miranda",
        "municipio": "Sucre",
        "tiene_electricidad": True,
        "tiene_agua": False,
        "tiene_oxigeno": False,
        "tiene_personal_tecnico": True,
        "contacto_responsable": "Responsable de guardia",
    },
    {
        "clave": "modulo_temporal_la_guaira",
        "nombre": "Modulo Temporal La Guaira",
        "tipo": CentroSalud.Tipo.MODULO_TEMPORAL,
        "estado_operativo": CentroSalud.EstadoOperativo.OPERATIVO,
        "geolocalizacion": "10.6016,-66.9346",
        "estado": "La Guaira",
        "municipio": "Vargas",
        "tiene_electricidad": True,
        "tiene_agua": True,
        "tiene_oxigeno": False,
        "tiene_personal_tecnico": False,
        "contacto_responsable": "Punto focal modulo",
    },
    {
        "clave": "refugio_charallave",
        "nombre": "Refugio Charallave",
        "tipo": CentroSalud.Tipo.REFUGIO,
        "estado_operativo": CentroSalud.EstadoOperativo.OPERATIVO,
        "geolocalizacion": "10.2425,-66.8572",
        "estado": "Miranda",
        "municipio": "Cristobal Rojas",
        "tiene_electricidad": False,
        "tiene_agua": True,
        "tiene_oxigeno": False,
        "tiene_personal_tecnico": False,
        "contacto_responsable": "Coordinacion refugio",
    },
)

USUARIOS: tuple[UsuarioSeed, ...] = (
    UsuarioSeed(
        username="nexo_admin",
        rol=Usuario.Rol.ADMIN,
        organizacion_clave="digisalud",
        email="admin@nexo.local",
        first_name="Admin",
        is_staff=True,
        is_superuser=True,
    ),
    UsuarioSeed(
        username="nexo_coordinador",
        rol=Usuario.Rol.COORDINADOR,
        organizacion_clave="digisalud",
        email="coordinador@nexo.local",
        first_name="Coordinador",
        is_staff=True,
    ),
    UsuarioSeed(
        username="nexo_campo",
        rol=Usuario.Rol.CAMPO,
        organizacion_clave="voluntarios_campo",
        email="campo@nexo.local",
        first_name="Campo",
    ),
    UsuarioSeed(
        username="nexo_lectura",
        rol=Usuario.Rol.LECTURA,
        organizacion_clave="alianza_medica_caracas",
        email="lectura@nexo.local",
        first_name="Lectura",
    ),
)


def _upsert_organizaciones() -> dict[str, Organizacion]:
    organizaciones: dict[str, Organizacion] = {}
    for dato in ORGANIZACIONES:
        clave = dato["clave"]
        valores = {k: v for k, v in dato.items() if k != "clave"}
        organizacion, _ = Organizacion.objects.update_or_create(
            id=uuid_seed(f"organizacion:{clave}"),
            defaults=valores,
        )
        organizaciones[clave] = organizacion
    return organizaciones


def _upsert_catalogos() -> None:
    for dato in CATALOGOS:
        catalogo = Catalogo.objects.filter(codigo=dato["codigo"]).first()
        if catalogo is None:
            catalogo = Catalogo(
                id=uuid_seed(f"catalogo:{dato['codigo']}"),
                codigo=dato["codigo"],
            )
        catalogo.nombre = dato["nombre"]
        catalogo.categoria = dato["categoria"]
        catalogo.unidad = dato["unidad"]
        catalogo.activo = True
        catalogo.save()


def _upsert_centros() -> None:
    for dato in CENTROS_SALUD:
        clave = dato["clave"]
        valores = {k: v for k, v in dato.items() if k != "clave"}
        CentroSalud.objects.update_or_create(
            id=uuid_seed(f"centro_salud:{clave}"),
            defaults=valores,
        )


def _upsert_usuarios(
    organizaciones: dict[str, Organizacion],
    password_inicial: str | None,
    reset_passwords: bool,
) -> None:
    for dato in USUARIOS:
        defaults = {
            "rol": dato.rol,
            "organizacion": organizaciones[dato.organizacion_clave],
            "email": dato.email,
            "first_name": dato.first_name,
            "last_name": dato.last_name,
            "is_staff": dato.is_staff,
            "is_superuser": dato.is_superuser,
            "is_active": True,
        }
        usuario, creado = Usuario.objects.update_or_create(
            username=dato.username,
            defaults=defaults,
        )
        if password_inicial and (creado or reset_passwords):
            usuario.password = make_password(password_inicial)
            usuario.save(update_fields=["password"])
        elif creado and not password_inicial:
            usuario.set_unusable_password()
            usuario.save(update_fields=["password"])


def ejecutar_seed_inicial(
    *,
    crear_usuarios: bool = True,
    password_inicial: str | None = None,
    reset_passwords: bool = False,
) -> dict[str, int]:
    """Carga datos base idempotentes para dejar Nexo listo para operar."""

    organizaciones = _upsert_organizaciones()
    _upsert_catalogos()
    _upsert_centros()
    if crear_usuarios:
        _upsert_usuarios(organizaciones, password_inicial, reset_passwords)

    return {
        "organizaciones": len(ORGANIZACIONES),
        "catalogos": len(CATALOGOS),
        "centros_salud": len(CENTROS_SALUD),
        "usuarios": len(USUARIOS) if crear_usuarios else 0,
    }
