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

#un comen
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