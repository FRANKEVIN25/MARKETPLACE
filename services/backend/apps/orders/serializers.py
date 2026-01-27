"""
Serializers de Orders - APIs para Svelte
"""
from rest_framework import serializers
from .models import Order, SupplierOrder, OrderItem
from apps.products.serializers import ProductListSerializer
from decimal import Decimal


class OrderItemListSerializer(serializers.ModelSerializer):
    """Serializer para items dentro de una orden"""
    product_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'sku', 'name', 'quantity',
            'unit_price', 'tax_percent', 'tax_amount',
            'total_price', 'product', 'product_detail'
        ]
        read_only_fields = ['id', 'tax_amount', 'total_price', 'product_detail']
    
    def get_product_detail(self, obj):
        """Info mínima del producto"""
        if obj.product:
            return {
                'id': obj.product.id,
                'name': obj.product.name,
                'reference': obj.product.reference,
            }
        return None


class SupplierOrderListSerializer(serializers.ModelSerializer):
    """Serializer para SupplierOrder en listados"""
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    item_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = SupplierOrder
        fields = [
            'id', 'provider', 'provider_name', 'status',
            'status_display', 'subtotal', 'tax_amount',
            'shipping_cost', 'discount_amount', 'total',
            'item_count', 'created_at'
        ]
        read_only_fields = fields


class SupplierOrderDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado para SupplierOrder con items"""
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    item_count = serializers.IntegerField(read_only=True)
    items = OrderItemListSerializer(many=True, read_only=True)
    
    class Meta:
        model = SupplierOrder
        fields = [
            'id', 'order', 'provider', 'provider_name',
            'status', 'status_display', 'company_id', 'warehouse_id',
            'subtotal', 'tax_amount', 'shipping_cost',
            'discount_amount', 'total', 'item_count',
            'items', 'confirmed_at', 'shipped_at',
            'completed_at', 'created_at', 'updated_at'
        ]
        read_only_fields = fields


class OrderListSerializer(serializers.ModelSerializer):
    """Serializer para listado de órdenes (optimizado)"""
    customer_name = serializers.CharField(source='customer.user.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    supplier_count = serializers.IntegerField(read_only=True)
    item_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer', 'customer_name',
            'status', 'status_display', 'total', 'currency',
            'supplier_count', 'item_count', 'created_at', 'paid_at'
        ]
        read_only_fields = fields


class OrderDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado de orden con todos los detalles"""
    customer_name = serializers.CharField(source='customer.user.get_full_name', read_only=True)
    customer_email = serializers.CharField(source='customer.user.email', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    supplier_count = serializers.IntegerField(read_only=True)
    item_count = serializers.IntegerField(read_only=True)
    
    # SupplierOrders con sus items
    supplier_orders = SupplierOrderDetailSerializer(many=True, read_only=True)
    
    # Dirección de envío
    shipping_address_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer', 'customer_name',
            'customer_email', 'status', 'status_display',
            'subtotal', 'discount_total', 'shipping_total',
            'tax_total', 'total', 'currency',
            'supplier_count', 'item_count',
            'shipping_address', 'shipping_address_detail',
            'supplier_orders', 'notes',
            'created_at', 'paid_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'order_number', 'status', 'subtotal',
            'discount_total', 'shipping_total', 'tax_total',
            'total', 'supplier_count', 'item_count',
            'supplier_orders', 'created_at', 'paid_at', 'updated_at'
        ]
    
    def get_shipping_address_detail(self, obj):
        """Detalles de dirección de envío"""
        if obj.shipping_address:
            return {
                'id': obj.shipping_address.id,
                'contact_name': obj.shipping_address.contact_name,
                'contact_phone': obj.shipping_address.contact_phone,
                'address': obj.shipping_address.address,
                'city': obj.shipping_address.city,
                'province': obj.shipping_address.province,
                'postal_code': obj.shipping_address.postal_code,
                'address_type': obj.shipping_address.get_address_type_display(),
            }
        return None


class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear órdenes"""
    
    class Meta:
        model = Order
        fields = [
            'customer', 'shipping_address', 'notes', 'currency'
        ]
        read_only_fields = ['currency']
    
    def validate_shipping_address(self, value):
        """Validar que la dirección pertenece al cliente"""
        request = self.context.get('request')
        customer = self.initial_data.get('customer')
        
        if value and value.customer_id != customer:
            raise serializers.ValidationError(
                "La dirección de envío debe pertenecer al cliente"
            )
        
        return value
    
    def create(self, validated_data):
        """Crear orden con número único"""
        from datetime import datetime
        
        # Generar número de orden único
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        order_number = f"ORD-{timestamp}"
        
        validated_data['order_number'] = order_number
        validated_data['status'] = 'borrador'
        
        return super().create(validated_data)


class OrderUpdateStatusSerializer(serializers.ModelSerializer):
    """Serializer para actualizar estado de orden"""
    
    class Meta:
        model = Order
        fields = ['status']
    
    def validate_status(self, value):
        """Validar transiciones de estado válidas"""
        instance = self.instance
        current_status = instance.status
        
        # Validaciones de transición
        if current_status == 'completado' and value != 'completado':
            raise serializers.ValidationError("No puedes cambiar una orden completada")
        
        if current_status == 'cancelado' and value != 'cancelado':
            raise serializers.ValidationError("No puedes cambiar una orden cancelada")
        
        if current_status == 'pagado' and value == 'pago_pendiente':
            raise serializers.ValidationError("No puedes volver de pagado a pago pendiente")
        
        return value


class SupplierOrderUpdateStatusSerializer(serializers.ModelSerializer):
    """Serializer para actualizar estado de SupplierOrder"""
    
    class Meta:
        model = SupplierOrder
        fields = ['status']
    
    def validate_status(self, value):
        """Validar transiciones de estado"""
        instance = self.instance
        current_status = instance.status
        
        if current_status == 'completed' and value != 'completed':
            raise serializers.ValidationError("No puedes cambiar una SupplierOrder completada")
        
        if current_status == 'cancelled' and value != 'cancelled':
            raise serializers.ValidationError("No puedes cambiar una SupplierOrder cancelada")
        
        return value


class OrderSummarySerializer(serializers.ModelSerializer):
    """Serializer sumario para cart/checkout"""
    supplier_summaries = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status',
            'subtotal', 'discount_total', 'shipping_total',
            'tax_total', 'total', 'currency',
            'supplier_summaries'
        ]
        read_only_fields = fields
    
    def get_supplier_summaries(self, obj):
        """Resumen por proveedor"""
        summaries = []
        for sup_order in obj.supplier_orders.all():
            summaries.append({
                'provider_id': sup_order.provider.id,
                'provider_name': sup_order.provider.name,
                'item_count': sup_order.item_count,
                'total': str(sup_order.total),
                'status': sup_order.get_status_display(),
            })
        return summaries
