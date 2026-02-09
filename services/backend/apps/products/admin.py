"""
Admin de Productos
"""
from mptt.admin import MPTTModelAdmin
from .models import Category, Product, CompatibilidadProducto
from django.contrib import admin
from apps.marketplace.models import Member


@admin.register(Category)
class CategoryAdmin(MPTTModelAdmin):
    list_display = ['name', 'parent', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'slug']
    readonly_fields = ['slug', 'created_at', 'updated_at']
    mptt_level_indent = 20


class CompatibilidadProductoInline(admin.TabularInline):
    model = CompatibilidadProducto
    extra = 1
    autocomplete_fields = ['variante']
    fields = ['variante', 'notas_instalacion']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'reference',
        'provider',
        'price',
        'stock',
        'is_active',
        'es_universal',
        'is_synced',
        'created_at'
    ]
    list_filter = ['is_active', 'product_type', 'category', 'provider', 'created_at']
    search_fields = ['name', 'reference', 'manufacturer_code', 'sku', 'barcode']
    readonly_fields = [
        'slug',
        'odoo_product_id',
        'odoo_template_id',
        'last_synced_at',
        'last_sync_at',
        'created_at',
        'updated_at'
    ]
    inlines = [CompatibilidadProductoInline]
    
    fieldsets = (
        ('Proveedor', {
            'fields': ('provider',)
        }),
        ('Información Básica', {
            'fields': (
                'name', 
                'reference', 
                'sku',
                'manufacturer_code',
                'barcode',
                'product_type',
                'price',
                'cost',
                'is_active', 
                'description', 
                'image', 
                'slug'
            )
        }),
        ('Stock', {
            'fields': ('stock', 'weight')
        }),
        ('Clasificación', {
            'fields': ('category', 'es_universal')
        }),
        ('Integración Odoo', {
            'fields': ('odoo_product_id', 'odoo_template_id', 'last_synced_at', 'last_sync_at'),
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


@admin.register(CompatibilidadProducto)
class CompatibilidadesAdmin(admin.ModelAdmin):
    list_display = ['producto', 'variante', 'notas_instalacion']
    list_filter = ['producto__provider']
    autocomplete_fields = ['producto', 'variante']
    search_fields = [
        'producto__name',
        'producto__reference',
        'variante__modelo__nombre',
        'variante__modelo__marca__nombre'
    ]