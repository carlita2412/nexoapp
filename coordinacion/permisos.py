"""
Control de acceso por rol (RBAC) para Nexo.

Reglas de oro aplicadas (PROMPT_MAESTRO §2.6, §2.7, §6):
- Acceso por rol en cada endpoint; nunca exponer escritura a anónimos.
- Neutralidad: el permiso depende del ROL, no de la organización. Ninguna
  organización tiene privilegio sobre otra; Digisalud opera la infraestructura.
- Mínimo privilegio: lectura por defecto, escritura solo a roles habilitados.

Roles (coordinacion.Usuario.Rol):
    admin       -> todo
    coordinador -> coordina la alianza: catálogo, centros, claims, captura
    campo        -> captura en terreno: centros, necesidades, donaciones, envíos,
                    claim de necesidades, push de sync
    lectura      -> solo lectura (donantes/prensa/observadores)
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Usuario

# Conjuntos de roles reutilizables
ROL = Usuario.Rol
TODOS_OPERATIVOS = {ROL.ADMIN, ROL.COORDINADOR, ROL.CAMPO}
SOLO_COORDINACION = {ROL.ADMIN, ROL.COORDINADOR}
SOLO_ADMIN = {ROL.ADMIN}


def rol_de(usuario) -> str | None:
    """Devuelve el rol del usuario autenticado, o None si no aplica."""
    if not usuario or not usuario.is_authenticated:
        return None
    return getattr(usuario, "rol", None)


def puede_escribir(usuario, roles_permitidos) -> bool:
    """True si el usuario puede escribir según su rol (superuser siempre puede)."""
    if not usuario or not usuario.is_authenticated:
        return False
    if usuario.is_superuser:
        return True
    return rol_de(usuario) in roles_permitidos


class PermisoPorRol(BasePermission):
    """
    Permiso base para ViewSets.

    - Métodos seguros (GET/HEAD/OPTIONS): cualquier usuario autenticado, incluido
      el rol `lectura`.
    - Métodos de escritura (POST/PUT/PATCH/DELETE): solo roles declarados en el
      atributo `roles_escritura` de la vista. Por defecto, solo admin (seguro).

    El superusuario de Django siempre puede (operación de la infraestructura).
    """

    mensaje_no_autenticado = "Autenticación requerida."
    message = "Tu rol no tiene permiso para esta acción."

    def has_permission(self, request, view) -> bool:
        usuario = request.user
        if not usuario or not usuario.is_authenticated:
            self.message = self.mensaje_no_autenticado
            return False

        if request.method in SAFE_METHODS:
            return True

        roles = getattr(view, "roles_escritura", SOLO_ADMIN)
        return puede_escribir(usuario, roles)


class EsCoordinacionParaEscribir(PermisoPorRol):
    """Escritura solo para admin/coordinador (p. ej. asignaciones manuales)."""

    def has_permission(self, request, view) -> bool:
        if request.user and request.user.is_authenticated and request.method in SAFE_METHODS:
            return True
        return puede_escribir(request.user, SOLO_COORDINACION)
