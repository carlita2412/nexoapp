from rest_framework import serializers

from .models import (
    Asignacion,
    Catalogo,
    CentroSalud,
    Donacion,
    Envio,
    Necesidad,
    Organizacion,
)


class OrganizacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organizacion
        fields = "__all__"


class CatalogoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Catalogo
        fields = "__all__"


class CentroSaludSerializer(serializers.ModelSerializer):
    class Meta:
        model = CentroSalud
        fields = "__all__"


class NecesidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Necesidad
        fields = "__all__"


class DonacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Donacion
        fields = "__all__"


class AsignacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asignacion
        fields = "__all__"


class EnvioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Envio
        fields = "__all__"


class CandidatoDonacionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    item = serializers.CharField()
    donante = serializers.CharField()
    cantidad_disponible = serializers.IntegerField()
    condicion = serializers.CharField()
    ubicacion_texto = serializers.CharField()
    compatible = serializers.BooleanField()
    motivo = serializers.CharField()
    puntaje = serializers.IntegerField()


class ClaimSerializer(serializers.Serializer):
    donacion_id = serializers.UUIDField()
    cantidad_asignada = serializers.IntegerField(min_value=1)
    organizacion_responsable_id = serializers.UUIDField()
    idempotency_key = serializers.UUIDField(required=False)


class EventoSyncSerializer(serializers.Serializer):
    idempotency_key = serializers.UUIDField()
    client_timestamp = serializers.DateTimeField(required=False)
    entity = serializers.CharField()
    payload = serializers.DictField()


class SyncPushSerializer(serializers.Serializer):
    eventos = EventoSyncSerializer(many=True)


from .models import Foto  # noqa: E402


class FotoSerializer(serializers.ModelSerializer):
    """Lectura: metadatos + URL de la imagen comprimida."""

    url = serializers.SerializerMethodField()

    class Meta:
        model = Foto
        fields = (
            "id",
            "envio",
            "estado",
            "bytes_original",
            "bytes_comprimida",
            "url",
            "error_detalle",
            "created_at",
        )

    def get_url(self, obj):
        if not obj.comprimida:
            return None
        request = self.context.get("request")
        url = obj.comprimida.url
        return request.build_absolute_uri(url) if request else url


class FotoSubidaSerializer(serializers.Serializer):
    """Escritura: subida multipart de una foto de entrega."""

    idempotency_key = serializers.UUIDField()
    envio = serializers.PrimaryKeyRelatedField(queryset=Envio.objects.all())
    imagen = serializers.ImageField()
