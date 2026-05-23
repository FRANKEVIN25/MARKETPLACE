"""
Serializers de Products - APIs para Svelte
"""
from rest_framework import serializers
from .models import Category, Product, Store, CompatibilidadProducto


class CategorySerializer(serializers.ModelSerializer):
    children_count = serializers.IntegerField(source='get_descendant_count', read_only=True)
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'parent', 'import_code',
            'description',
            'is_active', 'children_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'import_code', 'created_at', 'updated_at']


class PublicCategoryTreeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    children_count = serializers.SerializerMethodField()
    level = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'parent', 'import_code',
            'description', 'is_active', 'level', 'children_count',
            'children',
        ]
        read_only_fields = fields

    def get_children_count(self, obj):
        return len(self.get_children(obj))

    def get_children(self, obj):
        children = list(obj.children.filter(is_active=True).order_by('import_code'))
        return PublicCategoryTreeSerializer(children, many=True, context=self.context).data


class StoreSerializer(serializers.ModelSerializer):
    """Tiendas físicas del proveedor (puntos de retiro)."""
    provider_name = serializers.CharField(source='provider.name', read_only=True)

    class Meta:
        model = Store
        fields = [
            'id', 'provider', 'provider_name',
            'name', 'city', 'address', 'phone',
            'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['provider', 'provider_name', 'created_at', 'updated_at']


class ProductDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado de producto."""
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    provider_slug = serializers.CharField(source='provider.slug', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    autopart_side_display = serializers.CharField(source='get_autopart_side_display', read_only=True)
    autopart_quality_display = serializers.CharField(source='get_autopart_quality_display', read_only=True)
    is_synced = serializers.BooleanField(read_only=True)
    provider_group = serializers.IntegerField(source='provider.id', read_only=True)
    total_stock = serializers.IntegerField(source='total_stock_cached', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'reference', 'slug',
            'provider_group', 'provider_name', 'provider_slug',
            'product_type', 'manufacturer_code',
            'description', 'image_url',
            'price', 'tax_percent',
            'category', 'category_name',
            'is_active', 'is_synced',
            'total_stock',
            'autopart_side', 'autopart_side_display',
            'autopart_quality', 'autopart_quality_display',
            'es_universal',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'slug', 'is_synced', 'provider_group', 'provider_name', 'provider_slug',
            'odoo_product_id', 'odoo_template_id',
            'last_sync_at', 'created_at', 'updated_at',
            'total_stock'
        ]

    def validate(self, data):
        request = self.context.get('request')
        if request and hasattr(request, 'current_provider'):
            data['provider'] = request.current_provider
        return data


class ProductListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listados (mejor rendimiento)."""
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    provider_slug = serializers.CharField(source='provider.slug', read_only=True)
    provider_group = serializers.IntegerField(source='provider.id', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    autopart_side_display = serializers.CharField(source='get_autopart_side_display', read_only=True)
    autopart_quality_display = serializers.CharField(source='get_autopart_quality_display', read_only=True)
    total_stock = serializers.IntegerField(source='total_stock_cached', read_only=True)
    is_synced = serializers.BooleanField(read_only=True)
    price_with_tax = serializers.FloatField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'reference', 'slug',
            'provider_group', 'provider_name', 'provider_slug', 'product_type',
            'price', 'price_with_tax', 'tax_percent',
            'category_name', 'image_url',
            'autopart_side', 'autopart_side_display',
            'autopart_quality', 'autopart_quality_display',
            'is_active', 'is_published', 'total_stock',
            'is_synced', 'created_at'
        ]
        read_only_fields = fields


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer para crear/actualizar productos."""

    class Meta:
        model = Product
        fields = [
            'name', 'reference', 'product_type',
            'manufacturer_code', 'description',
            'price', 'tax_percent',
            'category', 'is_active', 'es_universal',
            'autopart_side', 'autopart_quality',
            'image_url', 'image_cloudinary_id'
        ]

    def validate_reference(self, value):
        request = self.context.get('request')
        provider = getattr(request, 'current_provider', None)
        if not provider:
            raise serializers.ValidationError("No provider found")
        qs = Product.objects.filter(provider=provider, reference=value)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)
        if qs.exists():
            raise serializers.ValidationError(
                "Un producto con esta referencia ya existe en tu catálogo"
            )
        return value

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("El precio debe ser mayor a 0")
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['provider'] = request.current_provider
        return super().create(validated_data)


class CompatibilidadProductoSerializer(serializers.ModelSerializer):
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
