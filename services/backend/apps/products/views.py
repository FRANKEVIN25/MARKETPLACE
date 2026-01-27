"""
Views de Products con Multi-Tenancy
"""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Category, Product, Warehouse, StockItem
from .serializers import (
    CategorySerializer, ProductListSerializer, ProductDetailSerializer,
    ProductCreateUpdateSerializer, WarehouseSerializer, StockItemSerializer,
    StockUpdateSerializer
)
from apps.marketplace.permissions import CanManageProducts, BelongsToGroup


class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet de Categorías (UNIVERSAL - sin filtro por grupo)
    """
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['parent', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet de Productos con Multi-Tenancy
    """
    permission_classes = [CanManageProducts, BelongsToGroup]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['active', 'product_type', 'category']
    search_fields = ['name', 'reference', 'manufacturer_code', 'description']
    ordering_fields = ['name', 'price', 'created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """
        Usar diferentes serializers según la acción:
        - list: ProductListSerializer (optimizado)
        - retrieve: ProductDetailSerializer (con stock por almacén)
        - create/update: ProductCreateUpdateSerializer (validaciones)
        """
        if self.action == 'retrieve':
            return ProductDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ProductCreateUpdateSerializer
        return ProductListSerializer
    
    def get_queryset(self):
        """
        Filtrar automáticamente por grupo del usuario.
        SuperAdmin ve todos los productos.
        """
        if self.request.user.is_superuser:
            return Product.objects.all()
        
        # Filtrar por grupo del usuario
        current_provider = getattr(self.request, 'current_provider', None)
        if current_provider:
            return Product.objects.for_group(current_provider)
        
        # Sin grupo = sin productos
        return Product.objects.none()
    
    def perform_create(self, serializer):
        """Asignar automáticamente el grupo al crear"""
        serializer.save(provider=self.request.current_provider)
    
    @action(detail=True, methods=['post'])
    def sync_to_odoo(self, request, pk=None):
        """
        Sincronizar producto individual a Odoo (ejemplo simple)
        """
        product = self.get_object()
        
        # TODO: Implementar sincronización real con Odoo
        # Por ahora, solo simulamos
        
        return Response({
            'status': 'success',
            'message': f'Producto {product.name} listo para sincronizar',
            'product_id': product.id
        })


class MarketplaceProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet público del marketplace (solo lectura).
    Muestra productos de TODOS los proveedores aprobados.
    """
    permission_classes = []  # Público
    authentication_classes = []  # No requiere autenticación
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'product_type']
    search_fields = ['name', 'reference', 'description']
    ordering_fields = ['name', 'price', 'created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """
        Usar diferentes serializers:
        - retrieve: ProductDetailSerializer (con stock por almacén)
        - list: ProductListSerializer (optimizado)
        """
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductListSerializer
    
    def get_queryset(self):
        """Solo productos activos de proveedores aprobados"""
        return Product.objects.for_marketplace()


class WarehouseViewSet(viewsets.ModelViewSet):
    """
    ViewSet de Almacenes (gestión por proveedor)
    """
    serializer_class = WarehouseSerializer
    permission_classes = [BelongsToGroup]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'city']
    search_fields = ['name', 'city', 'address']
    ordering_fields = ['name', 'city']
    ordering = ['name']
    
    def get_queryset(self):
        """Filtrar almacenes del proveedor actual"""
        if self.request.user.is_superuser:
            return Warehouse.objects.all()
        
        current_provider = getattr(self.request, 'current_provider', None)
        if current_provider:
            return Warehouse.objects.filter(provider=current_provider)
        
        return Warehouse.objects.none()
    
    def perform_create(self, serializer):
        """Asignar automáticamente el proveedor"""
        serializer.save(provider=self.request.current_provider)


class StockItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet de Stock (gestión de inventario)
    """
    permission_classes = [BelongsToGroup]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['warehouse', 'product']
    search_fields = ['product__name', 'product__reference', 'warehouse__name']
    ordering_fields = ['product', 'warehouse', 'quantity']
    ordering = ['warehouse', 'product']
    
    def get_serializer_class(self):
        """Usar StockUpdateSerializer para updates"""
        if self.action in ['update', 'partial_update']:
            return StockUpdateSerializer
        return StockItemSerializer
    
    def get_queryset(self):
        """Filtrar stock del proveedor actual"""
        if self.request.user.is_superuser:
            return StockItem.objects.all()
        
        current_provider = getattr(self.request, 'current_provider', None)
        if current_provider:
            return StockItem.objects.filter(
                product__provider=current_provider
            )
        
        return StockItem.objects.none()
