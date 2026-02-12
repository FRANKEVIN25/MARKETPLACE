"""
Admin de Productos - Configuración de Django Admin
"""
from mptt.admin import MPTTModelAdmin
from .models import Category, Product, CompatibilidadProducto, Warehouse, StockItem
from django.contrib import admin
from apps.marketplace.models import Member
from django.utils.html import format_html
from django.db.models import Sum


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


class StockItemInline(admin.TabularInline):
    """Inline para ver stock por almacén"""
    model = StockItem
    extra = 1
    fields = ['warehouse', 'quantity', 'is_low_stock', 'is_out_of_stock']
    readonly_fields = ['is_low_stock', 'is_out_of_stock', 'updated_at']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'reference',
        'provider',
        'price_with_tax',
        'total_stock_display',
        'active',
        'es_universal',
        'is_synced',
        'created_at'
    ]
    list_filter = ['active', 'product_type', 'category', 'provider', 'created_at']
    search_fields = ['name', 'reference', 'manufacturer_code', 'provider__name']
    readonly_fields = [
        'slug',
        'odoo_product_id',
        'odoo_template_id',
        'last_synced_at',
        'last_sync_at',
        'created_at',
        'updated_at',
        'total_stock',
    ]
    autocomplete_fields = ['provider', 'category']

    inlines = [StockItemInline, CompatibilidadProductoInline]

    fieldsets = (
        ('Proveedor', {
            'fields': ('provider',)
        }),
        ('Información Básica', {
            'fields': ('name', 'reference', 'manufacturer_code', 'product_type', 'price', 'tax_percent', 'active', 'description', 'image', 'slug')
        }),
        ('Clasificación', {
            'fields': ('category', 'es_universal')
        }),
        ('Stock', {
            'fields': ('total_stock',),
            'description': 'Stock total agregado de todos los almacenes'
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

    def price_with_tax(self, obj):
        """Mostrar precio con impuesto"""
        tax_amount = obj.price * (obj.tax_percent / 100)
        total = obj.price + tax_amount
        return f"${obj.price} + {obj.tax_percent}% = ${total:.2f}"
    price_with_tax.short_description = 'Precio (Base + IGV)'

    def total_stock_display(self, obj):
        """Mostrar stock total con color"""
        total = obj.total_stock
        if total == 0:
            color = 'red'
            label = 'SIN STOCK'
        elif total < 5:
            color = 'orange'
            label = f'BAJO ({total})'
        else:
            color = 'green'
            label = f'OK ({total})'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            label
        )
    total_stock_display.short_description = 'Stock Total'

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


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider', 'city', 'is_active', 'total_stock', 'created_at']
    list_filter = ['is_active', 'provider', 'city', 'created_at']
    search_fields = ['name', 'provider__name', 'city', 'address']
    readonly_fields = ['created_at', 'updated_at', 'total_stock']
    autocomplete_fields = ['provider']

    fieldsets = (
        ('Información Básica', {
            'fields': ('provider', 'name', 'city', 'address')
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Stock', {
            'fields': ('total_stock',),
            'description': 'Stock total de este almacén'
        }),
        ('Integración Odoo', {
            'fields': ('odoo_warehouse_id',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def total_stock(self, obj):
        """Mostrar stock total del almacén"""
        total = obj.total_stock
        if total == 0:
            return format_html('<span style="color: red;">Sin stock</span>')
        return format_html(
            '<span style="color: green; font-weight: bold;">{} unidades</span>',
            total
        )
    total_stock.short_description = 'Stock Total'


class StockItemFilter(admin.SimpleListFilter):
    """Filtro personalizado para stock bajo"""
    title = 'Estado de Stock'
    parameter_name = 'stock_status'

    def lookups(self, request, model_admin):
        return (
            ('out_of_stock', 'Sin Stock'),
            ('low_stock', 'Stock Bajo'),
            ('ok', 'Stock OK'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'out_of_stock':
            return queryset.filter(quantity=0)
        if self.value() == 'low_stock':
            return queryset.filter(quantity__gt=0, quantity__lt=5)
        if self.value() == 'ok':
            return queryset.filter(quantity__gte=5)
        return queryset


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = ['product', 'warehouse', 'quantity', 'stock_status', 'updated_at']
    list_filter = [StockItemFilter, 'warehouse__provider', 'warehouse', 'updated_at']
    search_fields = ['product__name', 'product__reference', 'warehouse__name', 'warehouse__provider__name']
    readonly_fields = ['created_at', 'updated_at', 'is_low_stock', 'is_out_of_stock']
    autocomplete_fields = ['product', 'warehouse']

    fieldsets = (
        ('Información', {
            'fields': ('product', 'warehouse', 'quantity')
        }),
        ('Estado', {
            'fields': ('is_low_stock', 'is_out_of_stock'),
            'description': 'Indicadores de stock'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def stock_status(self, obj):
        """Mostrar estado del stock con colores"""
        if obj.is_out_of_stock:
            return format_html(
                '<span style="color: white; background-color: red; padding: 3px 10px; border-radius: 3px; font-weight: bold;">SIN STOCK</span>'
            )
        elif obj.is_low_stock:
            return format_html(
                '<span style="color: white; background-color: orange; padding: 3px 10px; border-radius: 3px; font-weight: bold;">BAJO</span>'
            )
        return format_html(
            '<span style="color: white; background-color: green; padding: 3px 10px; border-radius: 3px; font-weight: bold;">OK</span>'
        )
    stock_status.short_description = 'Estado'

