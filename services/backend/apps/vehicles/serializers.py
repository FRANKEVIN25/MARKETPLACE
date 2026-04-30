"""
Serializers de Vehicles
"""
from rest_framework import serializers
from .models import Marca, ModeloVehiculo, Transmision, Traccion, Motor, VariantVehiculo


class MarcaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marca
        fields = ['id', 'nombre', 'slug', 'activo']
        read_only_fields = ['slug']


class ModeloVehiculoSerializer(serializers.ModelSerializer):
    marca_nombre = serializers.CharField(source='marca.nombre', read_only=True)
    
    class Meta:
        model = ModeloVehiculo
        fields = ['id', 'nombre', 'marca', 'marca_nombre', 'slug', 'activo']
        read_only_fields = ['slug']


class TransmisionSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    
    class Meta:
        model = Transmision
        fields = ['id', 'tipo', 'tipo_display', 'velocidades']


class TraccionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Traccion
        fields = ['id', 'tipo']


class MotorSerializer(serializers.ModelSerializer):
    combustible_display = serializers.CharField(source='get_combustible_display', read_only=True)
    
    class Meta:
        model = Motor
        fields = ['id', 'combustible', 'combustible_display', 'cilindrada_cc', 'codigo_motor', 'tecnologia']


class VariantVehiculoSerializer(serializers.ModelSerializer):
    marca_nombre = serializers.CharField(source='modelo.marca.nombre', read_only=True)
    modelo_nombre = serializers.CharField(source='modelo.nombre', read_only=True)
    motor_display = serializers.CharField(source='motor.__str__', read_only=True)
    transmision_display = serializers.CharField(source='transmision.__str__', read_only=True)
    traccion_display = serializers.CharField(source='traccion.__str__', read_only=True)
    
    class Meta:
        model = VariantVehiculo
        fields = [
            'id', 'import_code', 'modelo', 'marca_nombre', 'modelo_nombre',
            'motor', 'motor_display',
            'transmision', 'transmision_display',
            'traccion', 'traccion_display',
            'anio_desde', 'anio_hasta'
        ]
        read_only_fields = ['import_code']


class VariantVehiculoFilterSerializer(serializers.ModelSerializer):
    """Serializer simplificado para filtros públicos de variantes.

    Devuelve un único campo display_name concatenando motor, transmisión,
    tracción y rango de años, listo para usar en selects del frontend.
    """

    display_name = serializers.SerializerMethodField()

    class Meta:
        model = VariantVehiculo
        fields = ['id', 'display_name', 'modelo', 'anio_desde', 'anio_hasta']

    def get_display_name(self, obj):
        hasta = obj.anio_hasta or 'Actual'
        return (
            f"{obj.motor} | {obj.transmision} | {obj.traccion} "
            f"({obj.anio_desde}-{hasta})"
        )

