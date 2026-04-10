"""Views de Vehicles"""
from rest_framework import viewsets, generics
from rest_framework.permissions import IsAuthenticated, AllowAny

from apps.products.models import Product, CompatibilidadProducto
from .models import Marca, ModeloVehiculo, Transmision, Traccion, Motor, VariantVehiculo
from .serializers import (
    MarcaSerializer, ModeloVehiculoSerializer, TransmisionSerializer,
    TraccionSerializer, MotorSerializer, VariantVehiculoSerializer,
    VariantVehiculoFilterSerializer,
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
        'modelo__marca', 'motor', 'transmision', 'traccion'
    )
    serializer_class = VariantVehiculoSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['modelo', 'anio_desde', 'anio_hasta']
    search_fields = ['modelo__nombre', 'modelo__marca__nombre']
    ordering_fields = ['modelo__nombre', 'anio_desde']
    ordering = ['modelo__nombre', 'anio_desde']


class PublicMarcaListView(generics.ListAPIView):
    """Lista de marcas activas con productos compatibles en el marketplace.

    Endpoint público pensado para los filtros de la página de catálogo.
    """

    serializer_class = MarcaSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """Marcas activas priorizando las que tienen productos marketplace.

        Si aún no hay compatibilidades cargadas, devuelve todas las marcas activas
        para no dejar el selector vacío durante etapas tempranas del proyecto.
        """
        productos_marketplace = Product.objects.for_marketplace()

        qs_con_productos = Marca.objects.filter(
            activo=True,
            modelovehiculo__variantvehiculo__compatibilidadproducto__producto__in=productos_marketplace,
        ).distinct().order_by('nombre')

        if qs_con_productos.exists():
            return qs_con_productos

        # Fallback: todas las marcas activas
        return Marca.objects.filter(activo=True).order_by('nombre')


class PublicModeloListView(generics.ListAPIView):
    """Modelos activos para una marca con productos compatibles en marketplace."""

    serializer_class = ModeloVehiculoSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        productos_marketplace = Product.objects.for_marketplace()
        marca_id = self.request.query_params.get('marca_id')
        qs = ModeloVehiculo.objects.filter(
            activo=True,
            variantvehiculo__compatibilidadproducto__producto__in=productos_marketplace,
        ).select_related('marca')
        if marca_id:
            qs = qs.filter(marca_id=marca_id)
        return qs.distinct().order_by('marca__nombre', 'nombre')


class PublicVariantListView(generics.ListAPIView):
    """Variantes de vehículo para un modelo con productos compatibles.

    Devuelve un display_name ya formateado para mostrar en los selects.
    """

    serializer_class = VariantVehiculoFilterSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        productos_marketplace = Product.objects.for_marketplace()
        modelo_id = self.request.query_params.get('modelo_id')

        qs = VariantVehiculo.objects.filter(
            compatibilidadproducto__producto__in=productos_marketplace,
        ).select_related('modelo__marca', 'motor', 'transmision', 'traccion')

        if modelo_id:
            qs = qs.filter(modelo_id=modelo_id)

        return qs.distinct().order_by('modelo__nombre', 'anio_desde')

