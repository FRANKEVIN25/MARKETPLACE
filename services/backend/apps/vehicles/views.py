"""
Views de Vehicles
"""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Marca, ModeloVehiculo, Transmision, Traccion, Motor, VariantVehiculo
from .serializers import (
    MarcaSerializer, ModeloVehiculoSerializer, TransmisionSerializer,
    TraccionSerializer, MotorSerializer, VariantVehiculoSerializer
)


class MarcaViewSet(viewsets.ModelViewSet):
    queryset = Marca.objects.filter(activo=True)
    serializer_class = MarcaSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['nombre', 'activo']
    search_fields = ['nombre']
    ordering_fields = ['nombre']
    ordering = ['nombre']


class ModeloVehiculoViewSet(viewsets.ModelViewSet):
    queryset = ModeloVehiculo.objects.filter(activo=True).select_related('marca')
    serializer_class = ModeloVehiculoSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['marca', 'activo']
    search_fields = ['nombre', 'marca__nombre']
    ordering_fields = ['nombre', 'marca__nombre']
    ordering = ['marca__nombre', 'nombre']


class TransmisionViewSet(viewsets.ModelViewSet):
    queryset = Transmision.objects.all()
    serializer_class = TransmisionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['tipo']
    search_fields = ['tipo']
    ordering_fields = ['tipo', 'velocidades']
    ordering = ['tipo']


class TraccionViewSet(viewsets.ModelViewSet):
    queryset = Traccion.objects.all()
    serializer_class = TraccionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['tipo']
    search_fields = ['tipo']
    ordering_fields = ['tipo']
    ordering = ['tipo']


class MotorViewSet(viewsets.ModelViewSet):
    queryset = Motor.objects.all()
    serializer_class = MotorSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['combustible', 'cilindrada_cc']
    search_fields = ['codigo_motor', 'tecnologia']
    ordering_fields = ['combustible', 'cilindrada_cc']
    ordering = ['combustible', 'cilindrada_cc']


class VariantVehiculoViewSet(viewsets.ModelViewSet):
    queryset = VariantVehiculo.objects.select_related(
        'modelo', 'motor', 'transmision', 'traccion'
    )
    serializer_class = VariantVehiculoSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['modelo', 'anio_desde', 'anio_hasta']
    search_fields = ['modelo__nombre', 'modelo__marca__nombre']
    ordering_fields = ['modelo__nombre', 'anio_desde']
    ordering = ['modelo__nombre', 'anio_desde']
