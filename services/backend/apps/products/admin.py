"""
Admin de Productos - Configuración de Django Admin
"""
from mptt.admin import MPTTModelAdmin
from .models import Category, Product, CompatibilidadProducto, Store
from django.contrib import admin
from django.utils.html import format_html


@admin.register(Category)
class CategoryAdmin(MPTTModelAdmin):
    list_display = ['name', 'import_code', 'parent', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'slug', 'import_code']
    readonly_fields = ['slug', 'sync_key', 'import_code', 'created_at', 'updated_at']
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
        'price_with_tax',
        'total_stock_display',
        'is_active',
        'is_published',
        'es_universal',
        'is_synced',
        'created_at'
    ]
    list_filter = ['is_active', 'is_published', 'product_type', 'category', 'provider', 'created_at']
    search_fields = ['name', 'reference', 'manufacturer_code', 'provider__name']
    readonly_fields = [
        'slug',
        'odoo_product_id',
        'odoo_template_id',
        'last_sync_at',
        'total_stock_cached',
        'created_at',
        'updated_at',
    ]
    autocomplete_fields = ['provider', 'category']
    inlines = [CompatibilidadProductoInline]

    fieldsets = (
        ('Proveedor', {
            'fields': ('provider',)
        }),
        ('Información Básica', {
            'fields': ('name', 'reference', 'manufacturer_code', 'product_type', 'price', 'tax_percent', 'is_active', 'is_published', 'es_universal', 'description', 'image_url', 'image_cloudinary_id', 'slug')
        }),
        ('Clasificación', {
            'fields': ('category', 'autopart_side', 'autopart_quality')
        }),
        ('Stock', {
            'fields': ('total_stock_cached',),
            'description': 'Stock total sincronizado desde Odoo'
        }),
        ('Integración Odoo', {
            'fields': ('odoo_product_id', 'odoo_template_id', 'odoo_state', 'last_sync_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def price_with_tax(self, obj):
        tax_amount = obj.price * (obj.tax_percent / 100)
        total = obj.price + tax_amount
        return f"S/ {obj.price} + {obj.tax_percent}% = S/ {total:.2f}"
    price_with_tax.short_description = 'Precio (Base + IGV)'

    def total_stock_display(self, obj):
        total = obj.total_stock_cached
        if total == 0:
            color, label = 'red', 'SIN STOCK'
        elif total < 5:
            color, label = 'orange', f'BAJO ({total})'
        else:
            color, label = 'green', f'OK ({total})'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>', color, label
        )
    total_stock_display.short_description = 'Stock'

    def is_synced(self, obj):
        return obj.is_synced
    is_synced.boolean = True
    is_synced.short_description = 'Sincronizado'


@admin.register(CompatibilidadProducto)
class CompatibilidadesAdmin(admin.ModelAdmin):
    list_display = ['producto', 'variante', 'notas_instalacion']
    list_filter = ['producto__provider', 'producto__category']
    autocomplete_fields = ['producto', 'variante']
    search_fields = [
        'producto__name',
        'producto__reference',
        'variante__modelo__nombre',
        'variante__modelo__marca__nombre'
    ]


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider', 'city', 'phone', 'is_active', 'created_at']
    list_filter = ['is_active', 'provider', 'city']
    search_fields = ['name', 'provider__name', 'city', 'address']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['provider']

    fieldsets = (
        ('Información', {
            'fields': ('provider', 'name', 'city', 'address', 'phone')
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

