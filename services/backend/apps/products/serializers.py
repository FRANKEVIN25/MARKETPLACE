"""
Serializers de Products - APIs para Svelte
"""
from rest_framework import serializers
from .models import Category, Product, Warehouse, StockItem, CompatibilidadProducto


class CategorySerializer(serializers.ModelSerializer):
    children_count = serializers.IntegerField(source='get_descendant_count', read_only=True)
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'parent',
            'description', 'image',
            'is_active', 'children_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at']


class StockItemSerializer(serializers.ModelSerializer):
    """Serializer para stock - mostrar disponibilidad por almacén"""
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    warehouse_city = serializers.CharField(source='warehouse.city', read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    is_out_of_stock = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = StockItem
        fields = [
            'id', 'warehouse', 'warehouse_name', 'warehouse_city',
            'quantity', 'is_low_stock', 'is_out_of_stock',
            'updated_at'
        ]
        read_only_fields = ['warehouse', 'warehouse_name', 'warehouse_city', 'updated_at']


class WarehouseSerializer(serializers.ModelSerializer):
    """Serializer para almacenes"""
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    total_stock = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Warehouse
        fields = [
            'id', 'provider', 'provider_name',
            'name', 'city', 'address',
            'is_active', 'total_stock',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['provider_name', 'total_stock', 'created_at', 'updated_at']


class ProductDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado de producto con stock por almacén"""
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    is_synced = serializers.BooleanField(read_only=True)
    provider_group = serializers.IntegerField(source='provider.id', read_only=True)
    
    total_stock = serializers.IntegerField(read_only=True)
    stock_por_almacen = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'reference', 'slug',
            'provider_group', 'provider_name',
            'product_type', 'manufacturer_code',
            'description', 'image', 
            'price', 'tax_percent',
            'category', 'category_name',
            'is_active', 'is_synced',
            'total_stock', 'stock_por_almacen',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'slug', 'is_synced', 'provider_group', 'provider_name',
            'odoo_product_id', 'odoo_template_id',
            'last_synced_at', 'created_at', 'updated_at',
            'total_stock', 'stock_por_almacen'
        ]

    def get_stock_por_almacen(self, obj):
        # Devuelve lista de almacenes con stock para este producto
        stock_items = obj.stock_items.select_related('warehouse')
        return [
            {
                'warehouse_id': item.warehouse.id,
                'warehouse_name': item.warehouse.name,
                'warehouse_city': item.warehouse.city,
                'quantity': item.quantity
            }
            for item in stock_items
        ]
    
    def validate(self, data):
        """Validar que el producto pertenezca al proveedor del usuario"""
        request = self.context.get('request')
        if request and hasattr(request, 'current_provider'):
            data['provider'] = request.current_provider
        return data


class ProductListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listados (mejor rendimiento)"""
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    provider_group = serializers.IntegerField(source='provider.id', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    total_stock = serializers.IntegerField(read_only=True)
    is_synced = serializers.BooleanField(read_only=True)
    
    # Precio con impuesto
    price_with_tax = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'reference', 'slug',
            'provider_group', 'provider_name', 'product_type',
            'price', 'price_with_tax', 'tax_percent',
            'category_name', 'image',
            'is_active', 'total_stock',
            'is_synced', 'created_at'
        ]
        read_only_fields = fields
    
    def get_price_with_tax(self, obj):
        """Calcular precio con impuesto"""
        tax_amount = obj.price * (obj.tax_percent / 100)
        return float(obj.price + tax_amount)


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer para crear/actualizar productos"""
    
    class Meta:
        model = Product
        fields = [
            'name', 'reference', 'product_type',
            'manufacturer_code', 'description',
            'price', 'tax_percent',
            'category', 'is_active', 'es_universal',
            'image'
        ]
    
    def validate_reference(self, value):
        """Validar que la referencia sea única dentro del proveedor"""
        request = self.context.get('request')
        provider = getattr(request, 'current_provider', None)
        
        if not provider:
            raise serializers.ValidationError("No provider found")
        
        # Si es edición, excluir el producto actual
        if self.instance:
            if Product.objects.filter(
                provider=provider,
                reference=value
            ).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError(
                    "Un producto con esta referencia ya existe en tu catálogo"
                )
        else:
            if Product.objects.filter(provider=provider, reference=value).exists():
                raise serializers.ValidationError(
                    "Un producto con esta referencia ya existe en tu catálogo"
                )
        
        return value
    
    def validate_price(self, value):
        """Validar que el precio sea positivo"""
        if value <= 0:
            raise serializers.ValidationError("El precio debe ser mayor a 0")
        return value
    
    def create(self, validated_data):
        """Crear producto asignando automáticamente el proveedor"""
        request = self.context.get('request')
        validated_data['provider'] = request.current_provider
        return super().create(validated_data)


class StockUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizar stock"""
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    
    class Meta:
        model = StockItem
        fields = ['id', 'quantity', 'warehouse_name']
        read_only_fields = ['id', 'warehouse_name']
    
    def validate_quantity(self, value):
        """Validar que la cantidad sea no negativa"""
        if value < 0:
            raise serializers.ValidationError("La cantidad no puede ser negativa")
        return value


class CompatibilidadProductoSerializer(serializers.ModelSerializer):
    """Serializer para compatibilidades de productos"""
    variante_nombre = serializers.CharField(source='variante', read_only=True)
    producto_nombre = serializers.CharField(source='producto.name', read_only=True)
    
    class Meta:
        model = CompatibilidadProducto
        fields = [
            'id', 'producto', 'producto_nombre',
            'variante', 'variante_nombre',
            'notas_instalacion'
        ]
        read_only_fields = ['id', 'producto_nombre', 'variante_nombre']