"""
Serializers de Products
"""
from rest_framework import serializers
from .models import Category, Product


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


class ProductSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_synced = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'reference', 'slug',
            'provider', 'provider_name',
            'product_type', 'manufacturer_code',
            'description', 'image', 'price',
            'category', 'category_name',
            'active', 'is_synced',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'slug', 'is_synced',
            'odoo_product_id', 'odoo_template_id',
            'last_synced_at', 'created_at', 'updated_at'
        ]
    
    def validate(self, data):
        """Validar que el producto pertenezca al grupo del usuario"""
        request = self.context.get('request')
        if request and hasattr(request, 'current_provider'):
            data['provider'] = request.current_provider
        return data