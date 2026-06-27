from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    Asignacion,
    Catalogo,
    CentroSalud,
    Donacion,
    Envio,
    EventoSincronizado,
    Necesidad,
    Organizacion,
    RegistroAuditoria,
    Usuario,
)


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "email", "rol", "organizacion", "is_active")
    list_filter = ("rol", "is_active")


@admin.register(Organizacion)
class OrganizacionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "verificada", "activa")
    search_fields = ("nombre",)


@admin.register(Catalogo)
class CatalogoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "categoria", "unidad", "activo")
    search_fields = ("codigo", "nombre")
    list_filter = ("categoria", "activo")


@admin.register(CentroSalud)
class CentroSaludAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "tipo",
        "estado_operativo",
        "estado",
        "municipio",
        "tiene_electricidad",
        "tiene_agua",
        "tiene_oxigeno",
        "tiene_personal_tecnico",
    )
    search_fields = ("nombre", "estado", "municipio")
    list_filter = ("tipo", "estado_operativo", "estado")


@admin.register(Necesidad)
class NecesidadAdmin(admin.ModelAdmin):
    list_display = (
        "centro",
        "item",
        "cantidad_solicitada",
        "cantidad_cubierta",
        "nivel_triage",
        "estado",
        "reportada_por",
    )
    list_filter = ("nivel_triage", "estado")


@admin.register(Donacion)
class DonacionAdmin(admin.ModelAdmin):
    list_display = (
        "donante",
        "item",
        "cantidad",
        "condicion",
        "estado",
        "vencimiento",
    )
    list_filter = ("condicion", "estado")


@admin.register(Asignacion)
class AsignacionAdmin(admin.ModelAdmin):
    list_display = (
        "necesidad",
        "donacion",
        "cantidad_asignada",
        "organizacion_responsable",
        "estado_claim",
        "estado_logistico",
    )
    list_filter = ("estado_claim", "estado_logistico")


@admin.register(Envio)
class EnvioAdmin(admin.ModelAdmin):
    list_display = ("asignacion", "estado", "responsable", "timestamp_entrega")
    list_filter = ("estado",)


@admin.register(EventoSincronizado)
class EventoSincronizadoAdmin(admin.ModelAdmin):
    list_display = ("idempotency_key", "entity", "entity_id", "resultado", "creado_en")
    search_fields = ("idempotency_key", "entity")


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    list_display = ("accion", "entidad", "entidad_id", "creado_en")
    search_fields = ("accion", "entidad")