import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class BaseModelo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        abstract = True


class Organizacion(BaseModelo):
    class Tipo(models.TextChoices):
        ONG = "ong", "ONG"
        GOBIERNO = "gobierno", "Gobierno"
        VOLUNTARIO = "voluntario", "Voluntario"
        DONANTE_PRIVADO = "donante_privado", "Donante privado"
        CENTRO_SALUD = "centro_salud", "Centro de salud"

    nombre = models.CharField(max_length=255)
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    contacto = models.CharField(max_length=255, blank=True)
    verificada = models.BooleanField(default=False)
    activa = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class Catalogo(BaseModelo):
    class Categoria(models.TextChoices):
        EQUIPO_MEDICO = "equipo_medico", "Equipo médico"
        INSUMO = "insumo", "Insumo"
        MEDICAMENTO = "medicamento", "Medicamento"
        INFRAESTRUCTURA = "infraestructura", "Infraestructura"

    codigo = models.CharField(max_length=80, unique=True)
    nombre = models.CharField(max_length=255)
    categoria = models.CharField(max_length=30, choices=Categoria.choices)
    unidad = models.CharField(max_length=50, default="unidad")
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class CentroSalud(BaseModelo):
    class Tipo(models.TextChoices):
        HOSPITAL = "hospital", "Hospital"
        AMBULATORIO = "ambulatorio", "Ambulatorio"
        MODULO_TEMPORAL = "modulo_temporal", "Módulo temporal"
        REFUGIO = "refugio", "Refugio"

    class EstadoOperativo(models.TextChoices):
        OPERATIVO = "operativo", "Operativo"
        PARCIAL = "parcial", "Parcial"
        DANADO = "danado", "Dañado"
        NO_OPERATIVO = "no_operativo", "No operativo"

    nombre = models.CharField(max_length=255)
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    estado_operativo = models.CharField(
        max_length=30,
        choices=EstadoOperativo.choices,
        default=EstadoOperativo.OPERATIVO,
    )
    geolocalizacion = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=120)
    municipio = models.CharField(max_length=120)

    tiene_electricidad = models.BooleanField(default=False)
    tiene_agua = models.BooleanField(default=False)
    tiene_oxigeno = models.BooleanField(default=False)
    tiene_personal_tecnico = models.BooleanField(default=False)

    contacto_responsable = models.CharField(max_length=255, blank=True)
    ultima_actualizacion = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.nombre


class Necesidad(BaseModelo):
    class NivelTriage(models.TextChoices):
        CRITICO = "1_critico", "1 - Crítico"
        URGENTE = "2_urgente", "2 - Urgente"
        IMPORTANTE = "3_importante", "3 - Importante"
        RUTINARIO = "4_rutinario", "4 - Rutinario"

    class Estado(models.TextChoices):
        ABIERTA = "abierta", "Abierta"
        PARCIAL = "parcial", "Parcial"
        CUBIERTA = "cubierta", "Cubierta"
        CANCELADA = "cancelada", "Cancelada"

    centro = models.ForeignKey(CentroSalud, on_delete=models.PROTECT)
    item = models.ForeignKey(Catalogo, on_delete=models.PROTECT)
    cantidad_solicitada = models.PositiveIntegerField()
    cantidad_cubierta = models.PositiveIntegerField(default=0)
    nivel_triage = models.CharField(max_length=20, choices=NivelTriage.choices)
    requisitos_operacion = models.JSONField(default=dict, blank=True)
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.ABIERTA,
    )
    reportada_por = models.ForeignKey(Organizacion, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.item.nombre} - {self.centro.nombre}"


class Donacion(BaseModelo):
    class Condicion(models.TextChoices):
        NUEVO = "nuevo", "Nuevo"
        USADO_FUNCIONAL = "usado_funcional", "Usado funcional"
        REQUIERE_REPARACION = "requiere_reparacion", "Requiere reparación"
        REQUIERE_CALIBRACION = "requiere_calibracion", "Requiere calibración"

    class Estado(models.TextChoices):
        REGISTRADA = "registrada", "Registrada"
        DISPONIBLE = "disponible", "Disponible"
        ASIGNADA = "asignada", "Asignada"
        EN_TRANSITO = "en_transito", "En tránsito"
        ENTREGADA = "entregada", "Entregada"
        EN_USO = "en_uso", "En uso"
        DESCARTADA = "descartada", "Descartada"

    donante = models.ForeignKey(Organizacion, on_delete=models.PROTECT)
    item = models.ForeignKey(Catalogo, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    condicion = models.CharField(max_length=30, choices=Condicion.choices)
    vencimiento = models.DateField(null=True, blank=True)
    certificacion = models.TextField(blank=True)
    ubicacion_actual = models.CharField(max_length=100, blank=True)
    ubicacion_texto = models.CharField(max_length=255, blank=True)
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.REGISTRADA,
    )

    def __str__(self):
        return f"{self.item.nombre} x {self.cantidad}"


class Asignacion(BaseModelo):
    class EstadoClaim(models.TextChoices):
        TENTATIVA = "tentativa", "Tentativa"
        CONFIRMADA = "confirmada", "Confirmada"
        SUPERADA = "superada", "Superada"
        LIBERADA = "liberada", "Liberada"

    class EstadoLogistico(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EN_TRANSITO = "en_transito", "En tránsito"
        ENTREGADA = "entregada", "Entregada"
        CONFIRMADA = "confirmada", "Confirmada"

    necesidad = models.ForeignKey(Necesidad, on_delete=models.PROTECT)
    donacion = models.ForeignKey(Donacion, on_delete=models.PROTECT)
    cantidad_asignada = models.PositiveIntegerField()
    organizacion_responsable = models.ForeignKey(
        Organizacion,
        on_delete=models.PROTECT,
    )
    estado_claim = models.CharField(
        max_length=20,
        choices=EstadoClaim.choices,
        default=EstadoClaim.TENTATIVA,
    )
    claim_ts_cliente = models.DateTimeField()
    claim_ts_servidor = models.DateTimeField(null=True, blank=True)
    estado_logistico = models.CharField(
        max_length=20,
        choices=EstadoLogistico.choices,
        default=EstadoLogistico.PENDIENTE,
    )

    def __str__(self):
        return f"{self.necesidad} ← {self.donacion}"


class Envio(BaseModelo):
    class Estado(models.TextChoices):
        PREPARANDO = "preparando", "Preparando"
        EN_TRANSITO = "en_transito", "En tránsito"
        ENTREGADO = "entregado", "Entregado"
        INCIDENCIA = "incidencia", "Incidencia"

    asignacion = models.ForeignKey(Asignacion, on_delete=models.PROTECT)
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PREPARANDO,
    )
    responsable = models.CharField(max_length=255)
    foto_confirmacion_ref = models.CharField(max_length=500, blank=True)
    geolocalizacion_entrega = models.CharField(max_length=100, blank=True)
    timestamp_entrega = models.DateTimeField(null=True, blank=True)
    recibido_por = models.CharField(max_length=255, blank=True)
    notas = models.TextField(blank=True)

    def __str__(self):
        return f"Envío {self.id} - {self.estado}"


class EventoSincronizado(models.Model):
    idempotency_key = models.UUIDField(primary_key=True)
    entity = models.CharField(max_length=80)
    entity_id = models.UUIDField(null=True, blank=True)
    resultado = models.CharField(max_length=30)
    payload_hash = models.CharField(max_length=128, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.idempotency_key)


class RegistroAuditoria(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario_id = models.UUIDField(null=True, blank=True)
    accion = models.CharField(max_length=120)
    entidad = models.CharField(max_length=80)
    entidad_id = models.UUIDField(null=True, blank=True)
    detalle = models.JSONField(default=dict, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.accion} - {self.entidad}"


class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        ADMIN = "admin", "Admin"
        COORDINADOR = "coordinador", "Coordinador"
        CAMPO = "campo", "Campo"
        LECTURA = "lectura", "Lectura"

    organizacion = models.ForeignKey(
        Organizacion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    rol = models.CharField(
        max_length=20,
        choices=Rol.choices,
        default=Rol.CAMPO,
    )