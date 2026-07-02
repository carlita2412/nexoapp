from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .auth_views import LoginToken
from .fotos.vistas import FotoViewSet
from .kobo.views import webhook_kobo
from .transparencia import transparencia_donaciones, transparencia_resumen
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
router.register(r"fotos", FotoViewSet, basename="foto")

urlpatterns = [
    path("salud/", salud, name="salud"),
    path("auth/token/", LoginToken.as_view(), name="auth-token"),
    path("", include(router.urls)),
    path("sync/", sync, name="sync"),
    path("kobo/webhook/<str:tipo>/", webhook_kobo, name="kobo-webhook"),
    path("publico/transparencia/resumen/", transparencia_resumen, name="transparencia-resumen"),
    path("publico/transparencia/donaciones/", transparencia_donaciones, name="transparencia-donaciones"),
]
