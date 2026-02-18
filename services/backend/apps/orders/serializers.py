"""
Serializers para Orders - API REST
"""
from rest_framework import serializers
from .models import Order, SubOrder, OrderItem, PaymentProof
from apps.customer.models import Customer, Address
from apps.products.models import Product
from apps.marketplace.models import Provider
from decimal import Decimal


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer para items de orden"""
    product_name = serializers.CharField(read_only=True)
    product_sku = serializers.CharField(read_only=True)
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = [
            'id',
            'product',
            'product_name',
            'product_sku',
            'provider',
            'provider_name',
            'quantity',
            'unit_price',
            'igv_rate',
            'igv_amount',
            'discount',
            'subtotal',
        ]
        read_only_fields = ['product_name', 'product_sku', 'igv_rate', 'igv_amount', 'subtotal']


class PaymentProofSerializer(serializers.ModelSerializer):
    """Serializer para comprobantes de pago"""
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.get_full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = PaymentProof
        fields = [
            'id',
            'sub_order',
            'payment_method',
            'file',
            'operation_number',
            'amount',
            'uploaded_by',
            'uploaded_by_name',
            'uploaded_at',
            'verified_by',
            'verified_by_name',
            'verified_at',
            'verification_notes',
        ]
        read_only_fields = ['uploaded_by', 'uploaded_at', 'verified_by', 'verified_at']


class SubOrderSerializer(serializers.ModelSerializer):
    """Serializer para sub-órdenes"""
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    provider_tax_regime = serializers.CharField(source='provider.tax_regime', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    payment_proofs = PaymentProofSerializer(many=True, read_only=True)
    
    # Datos de pago del proveedor
    provider_payment_info = serializers.SerializerMethodField()
    
    class Meta:
        model = SubOrder
        fields = [
            'id',
            'sub_order_number',
            'order',
            'provider',
            'provider_name',
            'provider_tax_regime',
            'status',
            'subtotal',
            'igv_rate',
            'igv_amount',
            'total',
            'odoo_sale_id',
            'odoo_invoice_id',
            'rejection_reason',
            'tracking_number',
            'created_at',
            'updated_at',
            'confirmed_at',
            'items',
            'payment_proofs',
            'provider_payment_info',
        ]
        read_only_fields = [
            'sub_order_number',
            'subtotal',
            'igv_rate',
            'igv_amount',
            'total',
            'created_at',
            'updated_at',
            'confirmed_at',
        ]
    
    def get_provider_payment_info(self, obj):
        """Retorna información de pago del proveedor"""
        provider = obj.provider
        return {
            'banco_nombre': provider.banco_nombre,
            'banco_cuenta': provider.banco_cuenta,
            'banco_cci': provider.banco_cci,
            'yape_numero': provider.yape_numero,
            'plin_numero': provider.plin_numero,
        }


class OrderSerializer(serializers.ModelSerializer):
    """Serializer para órdenes principales"""
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    customer_email = serializers.EmailField(source='customer.user.email', read_only=True)
    shipping_address_detail = serializers.SerializerMethodField()
    sub_orders = SubOrderSerializer(many=True, read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    provider_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'customer',
            'customer_name',
            'customer_email',
            'status',
            'delivery_method',
            'shipping_address',
            'shipping_address_detail',
            'subtotal',
            'discount',
            'tax',
            'total',
            'customer_notes',
            'created_at',
            'updated_at',
            'provider_count',
            'sub_orders',
            'items',
        ]
        read_only_fields = [
            'order_number',
            'subtotal',
            'discount',
            'tax',
            'total',
            'created_at',
            'updated_at',
            'provider_count',
        ]
    
    def get_shipping_address_detail(self, obj):
        """Retorna dirección de envío formateada"""
        if obj.shipping_address:
            return {
                'contact_name': obj.shipping_address.contact_name,
                'contact_phone': obj.shipping_address.contact_phone,
                'full_address': obj.shipping_address.get_full_address(),
                'reference': obj.shipping_address.reference,
            }
        return None


class CreateOrderSerializer(serializers.Serializer):
    """Serializer para crear una orden nueva"""
    customer_id = serializers.IntegerField()
    shipping_address_id = serializers.IntegerField(required=False, allow_null=True)
    delivery_method = serializers.ChoiceField(choices=Order.DELIVERY_METHOD_CHOICES)
    customer_notes = serializers.CharField(required=False, allow_blank=True)
    
    # Lista de items
    items = serializers.ListField(
        child=serializers.DictField(),
        min_length=1
    )
    
    def validate_customer_id(self, value):
        """Validar que el cliente existe"""
        try:
            Customer.objects.get(id=value)
        except Customer.DoesNotExist:
            raise serializers.ValidationError("Cliente no encontrado")
        return value
    
    def validate_shipping_address_id(self, value):
        """Validar que la dirección existe"""
        if value:
            try:
                Address.objects.get(id=value)
            except Address.DoesNotExist:
                raise serializers.ValidationError("Dirección no encontrada")
        return value
    
    def validate_items(self, value):
        """Validar items de la orden"""
        if not value:
            raise serializers.ValidationError("La orden debe tener al menos un producto")
        
        for item in value:
            if 'product_id' not in item:
                raise serializers.ValidationError("Cada item debe tener 'product_id'")
            if 'quantity' not in item:
                raise serializers.ValidationError("Cada item debe tener 'quantity'")
            
            # Validar que el producto existe
            try:
                product = Product.objects.get(id=item['product_id'])
                if not product.is_active:
                    raise serializers.ValidationError(f"Producto {product.name} no está disponible")
                if product.stock < item['quantity']:
                    raise serializers.ValidationError(f"Stock insuficiente para {product.name}")
            except Product.DoesNotExist:
                raise serializers.ValidationError(f"Producto con ID {item['product_id']} no encontrado")
        
        return value
    
    def validate(self, data):
        """Validación global"""
        # Si es recojo en tienda, no requiere dirección
        if data['delivery_method'] != 'tienda' and not data.get('shipping_address_id'):
            raise serializers.ValidationError({
                'shipping_address_id': 'Dirección de envío requerida para este método de entrega'
            })
        
        return data


class UploadPaymentProofSerializer(serializers.Serializer):
    """Serializer para subir comprobante de pago"""
    sub_order_id = serializers.IntegerField()
    payment_method = serializers.ChoiceField(choices=PaymentProof.PAYMENT_METHOD_CHOICES)
    file = serializers.ImageField()
    operation_number = serializers.CharField(required=False, allow_blank=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    def validate_sub_order_id(self, value):
        """Validar que la sub-orden existe"""
        try:
            SubOrder.objects.get(id=value)
        except SubOrder.DoesNotExist:
            raise serializers.ValidationError("Sub-orden no encontrada")
        return value


class ConfirmPaymentSerializer(serializers.Serializer):
    """Serializer para confirmar/rechazar pago"""
    sub_order_id = serializers.IntegerField()
    action = serializers.ChoiceField(choices=['confirm', 'reject'])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
    
    def validate_sub_order_id(self, value):
        """Validar que la sub-orden existe"""
        try:
            SubOrder.objects.get(id=value)
        except SubOrder.DoesNotExist:
            raise serializers.ValidationError("Sub-orden no encontrada")
        return value
    
    def validate(self, data):
        """Validación global"""
        if data['action'] == 'reject' and not data.get('rejection_reason'):
            raise serializers.ValidationError({
                'rejection_reason': 'Debe proporcionar un motivo de rechazo'
            })
        return data
