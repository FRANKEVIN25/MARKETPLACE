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
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    
    class Meta:
        model = Traccion
        fields = ['id', 'tipo', 'tipo_display']


class MotorSerializer(serializers.ModelSerializer):
    combustible_display = serializers.CharField(source='get_combustible_display', read_only=True)
    
    class Meta:
        model = Motor
        fields = ['id', 'combustible', 'combustible_display', 'cilindrada_cc', 'codigo_motor', 'tecnologia']


class VariantVehiculoSerializer(serializers.ModelSerializer):
    modelo_nombre = serializers.CharField(source='modelo.nombre', read_only=True)
    motor_display = serializers.CharField(source='motor.__str__', read_only=True)
    transmision_display = serializers.CharField(source='transmision.__str__', read_only=True)
    traccion_display = serializers.CharField(source='traccion.__str__', read_only=True)
    
    class Meta:
        model = VariantVehiculo
        fields = [
            'id', 'modelo', 'modelo_nombre', 'motor', 'motor_display',
            'transmision', 'transmision_display', 'traccion', 'traccion_display',
            'anio_desde', 'anio_hasta'
        ]
