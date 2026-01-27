"""
Views de Orders - Marketplace Multiproveedor
"""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import Order, SupplierOrder, OrderItem
from .serializers import (
    OrderListSerializer, OrderDetailSerializer, OrderSummarySerializer,
    OrderCreateSerializer, OrderUpdateStatusSerializer,
    SupplierOrderListSerializer, SupplierOrderDetailSerializer,
    SupplierOrderUpdateStatusSerializer,
    OrderItemListSerializer
)


class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet de Órdenes
    
    Permisos:
    - list: Solo sus propias órdenes
    - retrieve: Solo sus propias órdenes
    - create: Cliente autenticado
    - update: Solo status (transiciones permitidas)
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'created_at']
    search_fields = ['order_number', 'customer__user__email']
    ordering_fields = ['created_at', 'total', 'status']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """
        Usar diferentes serializers según acción:
        - list: OrderListSerializer (resumen)
        - retrieve: OrderDetailSerializer (completo con proveedores e items)
        - create: OrderCreateSerializer
        - update/partial_update: OrderUpdateStatusSerializer (solo status)
        """
        if self.action == 'retrieve':
            return OrderDetailSerializer
        elif self.action == 'create':
            return OrderCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return OrderUpdateStatusSerializer
        elif self.action == 'summary':
            return OrderSummarySerializer
        return OrderListSerializer
    
    def get_queryset(self):
        """
        Filtrar órdenes según usuario:
        - SuperAdmin: todas
        - Staff: todas
        - Cliente: solo sus órdenes
        """
        user = self.request.user
        
        if user.is_superuser or user.is_staff:
            return Order.objects.all()
        
        # Cliente ve solo sus órdenes
        try:
            customer = user.customer_profile
            return Order.objects.filter(customer=customer)
        except:
            return Order.objects.none()
    
    def perform_create(self, serializer):
        """Asignar automáticamente el cliente al crear"""
        try:
            customer = self.request.user.customer_profile
            serializer.save(customer=customer)
        except:
            return Response(
                {'detail': 'Usuario no tiene perfil de cliente'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Resumen de orden (para cart/checkout)"""
        order = self.get_object()
        serializer = OrderSummarySerializer(order)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_as_paid(self, request, pk=None):
        """Marcar orden como pagada"""
        from django.utils import timezone
        order = self.get_object()
        
        if order.status not in ['pago_pendiente', 'borrador']:
            return Response(
                {'detail': 'Orden no puede ser marcada como pagada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'pagado'
        order.paid_at = timezone.now()
        order.save()
        
        return Response({
            'status': 'success',
            'message': 'Orden marcada como pagada',
            'order': OrderDetailSerializer(order).data
        })
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancelar orden"""
        order = self.get_object()
        
        if order.status == 'completado':
            return Response(
                {'detail': 'No puedes cancelar una orden completada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if order.status == 'cancelado':
            return Response(
                {'detail': 'Orden ya está cancelada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'cancelado'
        order.save()
        
        return Response({
            'status': 'success',
            'message': 'Orden cancelada',
            'order': OrderDetailSerializer(order).data
        })


class SupplierOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de SupplierOrders (solo lectura para clientes)
    
    Los proveedores pueden gestionar desde su dashboard específico.
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'provider', 'created_at']
    ordering_fields = ['created_at', 'total', 'status']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """
        Usar diferentes serializers:
        - retrieve: SupplierOrderDetailSerializer (con items)
        - list: SupplierOrderListSerializer (resumen)
        """
        if self.action == 'retrieve':
            return SupplierOrderDetailSerializer
        return SupplierOrderListSerializer
    
    def get_queryset(self):
        """
        Filtrar SupplierOrders según usuario:
        - SuperAdmin/Staff: todas
        - Cliente: solo de sus órdenes
        - Proveedor: solo las suyas
        """
        user = self.request.user
        
        if user.is_superuser or user.is_staff:
            return SupplierOrder.objects.all()
        
        # Cliente ve sus SupplierOrders
        try:
            customer = user.customer_profile
            return SupplierOrder.objects.filter(order__customer=customer)
        except:
            # Proveedor ve sus SupplierOrders
            try:
                provider = user.provider_memberships.first().provider
                return SupplierOrder.objects.filter(provider=provider)
            except:
                return SupplierOrder.objects.none()
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def update_status(self, request, pk=None):
        """
        Actualizar estado (solo para proveedores/staff)
        """
        supplier_order = self.get_object()
        
        # Verificar permisos (proveedor o admin)
        if not request.user.is_superuser:
            try:
                provider = request.user.provider_memberships.first().provider
                if supplier_order.provider != provider:
                    return Response(
                        {'detail': 'No tienes permisos para esta SupplierOrder'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except:
                return Response(
                    {'detail': 'No tienes permisos'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = SupplierOrderUpdateStatusSerializer(
            supplier_order,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrderItemViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de Items de Orden (solo lectura)
    """
    serializer_class = OrderItemListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['supplier_order', 'product']
    search_fields = ['name', 'sku']
    
    def get_queryset(self):
        """
        Filtrar items según usuario:
        - SuperAdmin/Staff: todos
        - Cliente: solo de sus órdenes
        """
        user = self.request.user
        
        if user.is_superuser or user.is_staff:
            return OrderItem.objects.all()
        
        # Cliente ve items de sus órdenes
        try:
            customer = user.customer_profile
            return OrderItem.objects.filter(
                supplier_order__order__customer=customer
            )
        except:
            return OrderItem.objects.none()

