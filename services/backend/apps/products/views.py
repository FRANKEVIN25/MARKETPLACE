"""
Views de Products con Multi-Tenancy
"""
from rest_framework import viewsets, filters, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Category, Product, Store
from .serializers import (
    CategorySerializer, ProductListSerializer, ProductDetailSerializer,
    ProductCreateUpdateSerializer, StoreSerializer
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


class PublicCategoryListView(generics.ListAPIView):
    """Lista pública de categorías activas para el marketplace.

    Solo lectura, sin autenticación, pensada para filtros de catálogo.
    """

    permission_classes = []  # Público
    authentication_classes = []
    serializer_class = CategorySerializer

    def get_queryset(self):
        return Category.objects.filter(is_active=True).order_by('name')


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet de Productos con Multi-Tenancy
    """
    permission_classes = [CanManageProducts, BelongsToGroup]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'is_published', 'product_type', 'category']
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
            qs = Product.objects.all()
        else:
            current_provider = getattr(self.request, 'current_provider', None)
            if not current_provider:
                return Product.objects.none()
            qs = Product.objects.for_provider(current_provider)

        return qs.select_related('provider', 'category')
    
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
        """Solo productos activos de proveedores aprobados, con filtros de vehículo y búsqueda.

        Filtros soportados (query params):
        - marca_id: ID de Marca (vehicles.Marca)
        - modelo_id: ID de ModeloVehiculo
        - variante_id: ID de VariantVehiculo
        - q: texto de búsqueda (alias amigable de search)
        - provider_id: ID de Provider (apps.marketplace.Provider)
        - es_universal: "true" | "false" para filtrar productos universales
        - category_id / category: ID de Category (incluye descendientes)
        - category_slug: slug de Category (incluye descendientes)
        """

        qs = Product.objects.for_marketplace().select_related('provider', 'category')

        request = self.request
        params = request.query_params

        marca_id = params.get('marca_id')
        modelo_id = params.get('modelo_id')
        variante_id = params.get('variante_id')
        q = params.get('q')
        provider_id = params.get('provider_id')
        es_universal = params.get('es_universal')
        category_id = params.get('category_id') or params.get('category')
        category_slug = params.get('category_slug')

        if marca_id:
            qs = qs.filter(
                compatibilidades__variante__modelo__marca_id=marca_id
            )

        if modelo_id:
            qs = qs.filter(
                compatibilidades__variante__modelo_id=modelo_id
            )

        if variante_id:
            qs = qs.filter(
                compatibilidades__variante_id=variante_id
            )

        # Filtro por proveedor (multi-tenant)
        if provider_id:
            qs = qs.filter(provider_id=provider_id)

        # Filtro por productos universales
        # es_universal=true  -> solo productos universales
        # es_universal=false -> solo productos no universales
        if es_universal is not None:
            value = str(es_universal).lower()
            if value in ['true', '1']:
                qs = qs.filter(es_universal=True)
            elif value in ['false', '0']:
                qs = qs.filter(es_universal=False)

        # Filtro por categoría (incluye descendientes en el árbol MPTT)
        if category_id or category_slug:
            try:
                if category_id:
                    base_category = Category.objects.get(id=category_id, is_active=True)
                else:
                    base_category = Category.objects.get(slug=category_slug, is_active=True)
            except Category.DoesNotExist:
                # Si la categoría no existe, devolver queryset vacío
                qs = qs.none()
            else:
                descendant_ids = base_category.get_descendants(include_self=True).values_list('id', flat=True)
                qs = qs.filter(category_id__in=descendant_ids)

        if q:
            from django.db.models import Q

            qs = qs.filter(
                Q(name__icontains=q)
                | Q(reference__icontains=q)
                | Q(description__icontains=q)
                | Q(manufacturer_code__icontains=q)
            )

        return qs.distinct()


class StoreViewSet(viewsets.ModelViewSet):
    """
    Tiendas físicas del proveedor (puntos de retiro).
    No gestiona stock — solo información de ubicación.
    """
    serializer_class = StoreSerializer
    permission_classes = [BelongsToGroup]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'city']
    search_fields = ['name', 'city', 'address']
    ordering_fields = ['name', 'city']
    ordering = ['name']

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Store.objects.all()
        current_provider = getattr(self.request, 'current_provider', None)
        if current_provider:
            return Store.objects.filter(provider=current_provider)
        return Store.objects.none()

    def perform_create(self, serializer):
        serializer.save(provider=self.request.current_provider)
