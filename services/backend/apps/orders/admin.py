"""
Admin de Orders - Configuración Django Admin
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Order, SupplierOrder, OrderItem


class OrderItemInline(admin.TabularInline):
    """Inline para ver items de una SupplierOrder"""
    model = OrderItem
    extra = 0
    fields = ['product', 'sku', 'name', 'quantity', 'unit_price', 'total_price']
    readonly_fields = ['sku', 'name', 'total_price']


class SupplierOrderInline(admin.TabularInline):
    """Inline para ver SupplierOrders de una Order"""
    model = SupplierOrder
    extra = 0
    fields = ['provider', 'status', 'subtotal', 'shipping_cost', 'total']
    readonly_fields = ['subtotal', 'shipping_cost', 'total']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number',
        'customer',
        'status_display',
        'supplier_count',
        'item_count',
        'total',
        'created_at'
    ]
    list_filter = ['status', 'created_at', 'paid_at']
    search_fields = ['order_number', 'customer__user__email', 'customer__user__first_name']
    readonly_fields = [
        'order_number', 'subtotal', 'discount_total',
        'shipping_total', 'tax_total', 'total',
        'created_at', 'updated_at'
    ]
    autocomplete_fields = ['customer', 'shipping_address']

    inlines = [SupplierOrderInline]

    fieldsets = (
        ('Información de Orden', {
            'fields': ('order_number', 'status', 'customer', 'created_at', 'updated_at')
        }),
        ('Envío', {
            'fields': ('shipping_address', 'paid_at'),
            'description': 'Información de envío y pago'
        }),
        ('Totales', {
            'fields': ('subtotal', 'discount_total', 'shipping_total', 'tax_total', 'total', 'currency'),
            'description': 'Montos calculados'
        }),
        ('Notas', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    def status_display(self, obj):
        """Mostrar estado con colores"""
        status_colors = {
            'borrador': 'gray',
            'pago_pendiente': 'orange',
            'pagado': 'blue',
            'procesando': 'purple',
            'completado': 'green',
            'cancelado': 'red',
        }
        color = status_colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Estado'

    def supplier_count(self, obj):
        """Contar proveedores"""
        count = obj.supplier_count
        return format_html(
            '<span style="background-color: lightblue; padding: 2px 8px; border-radius: 3px;">{} prov.</span>',
            count
        )
    supplier_count.short_description = 'Proveedores'

    def item_count(self, obj):
        """Contar items totales"""
        count = obj.item_count
        return format_html(
            '<span style="background-color: lightgreen; padding: 2px 8px; border-radius: 3px;">{} items</span>',
            count
        )
    item_count.short_description = 'Items'


@admin.register(SupplierOrder)
class SupplierOrderAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'order',
        'provider',
        'status_display',
        'item_count',
        'total',
        'created_at'
    ]
    list_filter = ['status', 'provider', 'created_at']
    search_fields = ['order__order_number', 'provider__name']
    readonly_fields = [
        'order', 'subtotal', 'tax_amount',
        'shipping_cost', 'discount_amount', 'total',
        'created_at', 'confirmed_at', 'shipped_at',
        'completed_at', 'updated_at'
    ]
    autocomplete_fields = ['order', 'provider']

    inlines = [OrderItemInline]

    fieldsets = (
        ('Información General', {
            'fields': ('order', 'provider', 'status', 'company_id')
        }),
        ('Cumplimiento', {
            'fields': ('warehouse_id', 'confirmed_at', 'shipped_at', 'completed_at')
        }),
        ('Totales', {
            'fields': ('subtotal', 'tax_amount', 'shipping_cost', 'discount_amount', 'total'),
            'description': 'Montos de esta SupplierOrder'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def status_display(self, obj):
        """Mostrar estado con colores"""
        status_colors = {
            'pending': 'gray',
            'confirmed': 'blue',
            'processing': 'purple',
            'shipped': 'orange',
            'completed': 'green',
            'cancelled': 'red',
        }
        color = status_colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Estado'

    def item_count(self, obj):
        """Contar items"""
        count = obj.item_count
        return format_html(
            '<span style="background-color: lightgreen; padding: 2px 8px; border-radius: 3px;">{}</span>',
            count
        )
    item_count.short_description = 'Items'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = [
        'supplier_order',
        'name',
        'sku',
        'quantity',
        'unit_price',
        'tax_percent',
        'total_with_tax',
        'created_at'
    ]
    list_filter = ['supplier_order__order__status', 'supplier_order__provider', 'created_at']
    search_fields = ['name', 'sku', 'supplier_order__order__order_number']
    readonly_fields = [
        'product', 'tax_amount', 'total_price',
        'created_at', 'updated_at'
    ]
    autocomplete_fields = ['supplier_order', 'product']

    fieldsets = (
        ('Información de Producto', {
            'fields': ('supplier_order', 'product', 'product_id_snapshot', 'sku', 'name')
        }),
        ('Cantidades y Precios', {
            'fields': ('quantity', 'unit_price', 'tax_percent', 'tax_amount', 'total_price')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def total_with_tax(self, obj):
        """Mostrar total con impuesto incluido"""
        total = obj.total_price + obj.tax_amount
        return format_html(
            '${:.2f} <small>(+ ${:.2f} impuesto)</small>',
            obj.total_price,
            obj.tax_amount
        )
    total_with_tax.short_description = 'Total'
