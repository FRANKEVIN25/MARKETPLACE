"""
Admin de Productos
"""
from django.contrib import admin
from mptt.admin import MPTTModelAdmin
from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(MPTTModelAdmin):
    list_display = ['name', 'parent', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'slug']
    readonly_fields = ['slug', 'created_at', 'updated_at']
    mptt_level_indent = 20


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'reference',
        'provider',
        'price',
        'active',
        'is_synced',
        'created_at'
    ]
    list_filter = ['active', 'product_type', 'provider', 'category', 'created_at']
    search_fields = ['name', 'reference', 'manufacturer_code']
    readonly_fields = [
        'slug',
        'odoo_product_id',
        'odoo_template_id',
        'last_synced_at',
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('Proveedor', {
            'fields': ('provider',)
        }),
        ('Información Básica', {
            'fields': ('name', 'reference', 'slug', 'product_type')
        }),
        ('Contenido', {
            'fields': ('description', 'image', 'manufacturer_code')
        }),
        ('Clasificación', {
            'fields': ('category',)
        }),
        ('Precio', {
            'fields': ('price',)
        }),
        ('Estado', {
            'fields': ('active',)
        }),
        ('Integración Odoo', {
            'fields': ('odoo_product_id', 'odoo_template_id', 'last_synced_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_synced(self, obj):
        return obj.is_synced
    
    is_synced.boolean = True
    is_synced.short_description = 'Sincronizado'