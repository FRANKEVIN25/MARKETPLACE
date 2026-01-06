"""
Views de Products con Multi-Tenancy
"""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer
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
    serializer_class = ProductSerializer
    permission_classes = [CanManageProducts, BelongsToGroup]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['active', 'product_type', 'category']
    search_fields = ['name', 'reference', 'manufacturer_code', 'description']
    ordering_fields = ['name', 'price', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Filtrar automáticamente por grupo del usuario.
        SuperAdmin ve todos los productos.
        """
        if self.request.user.is_superuser:
            return Product.objects.all()
        
        # Filtrar por grupo del usuario
        current_group = getattr(self.request, 'current_group', None)
        if current_group:
            return Product.objects.for_group(current_group)
        
        # Sin grupo = sin productos
        return Product.objects.none()
    
    def perform_create(self, serializer):
        """Asignar automáticamente el grupo al crear"""
        serializer.save(provider_group=self.request.current_group)
    
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
    serializer_class = ProductSerializer
    permission_classes = []  # Público
    authentication_classes = []  # No requiere autenticación
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'product_type']
    search_fields = ['name', 'reference', 'description']
    ordering_fields = ['name', 'price', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Solo productos activos de proveedores aprobados"""
        return Product.objects.for_marketplace()
