from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AsignacionViewSet,
    CatalogoViewSet,
    CentroSaludViewSet,
    DonacionViewSet,
    EnvioViewSet,
    NecesidadViewSet,
    OrganizacionViewSet,
    salud,
    sync,
)

router = DefaultRouter()
router.register(r"organizaciones", OrganizacionViewSet, basename="organizacion")
router.register(r"catalogos", CatalogoViewSet, basename="catalogo")
router.register(r"centros-salud", CentroSaludViewSet, basename="centro-salud")
router.register(r"necesidades", NecesidadViewSet, basename="necesidad")
router.register(r"donaciones", DonacionViewSet, basename="donacion")
router.register(r"asignaciones", AsignacionViewSet, basename="asignacion")
router.register(r"envios", EnvioViewSet, basename="envio")

urlpatterns = [
    path("salud/", salud, name="salud"),
    path("", include(router.urls)),
    path("sync/", sync, name="sync"),
]