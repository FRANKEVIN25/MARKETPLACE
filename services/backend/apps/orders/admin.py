"""
Admin para modelos de Orders
"""
from django.contrib import admin
from .models import Order, SubOrder, OrderItem, PaymentProof


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['name', 'sku', 'quantity', 'unit_price', 'tax_percent', 'tax_amount', 'total_price']
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'customer', 'status', 'total', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order_number', 'customer__user__email']
    readonly_fields = ['order_number', 'created_at', 'updated_at']


class PaymentProofInline(admin.TabularInline):
    model = PaymentProof
    extra = 0
    readonly_fields = [
        'status', 'payment_method', 'amount', 'operation_number',
        'file', 'uploaded_by', 'uploaded_at', 'verified_by', 'verified_at',
    ]
    fields = readonly_fields + ['rejection_reason']
    can_delete = False


@admin.register(SubOrder)
class SubOrderAdmin(admin.ModelAdmin):
    list_display = [
        'sub_order_number', 'provider', 'status',
        'payment_rejected', 'expired', 'odoo_sync_error',
        'total', 'created_at',
    ]
    list_filter = ['status', 'payment_rejected', 'expired', 'odoo_sync_error', 'provider', 'created_at']
    search_fields = ['sub_order_number', 'order__order_number', 'provider__name']
    readonly_fields = [
        'sub_order_number', 'order', 'provider',
        'created_at', 'updated_at', 'confirmed_at', 'shipped_at', 'delivered_at',
    ]

    fieldsets = (
        ('Información Básica', {
            'fields': ('sub_order_number', 'order', 'provider', 'status')
        }),
        ('Montos', {
            'fields': ('subtotal', 'igv_rate', 'igv_amount', 'total')
        }),
        ('Integración Odoo', {
            'fields': ('odoo_sale_id', 'odoo_invoice_id', 'odoo_sync_error', 'odoo_sync_error_detail')
        }),
        ('Flags de estado', {
            'fields': ('payment_rejected', 'expired', 'refunded'),
        }),
        ('Tracking', {
            'fields': ('tracking_number',)
        }),
        ('Notas / Reembolso', {
            'fields': ('refund_notes',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'confirmed_at', 'shipped_at', 'delivered_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [PaymentProofInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'sub_order', 'product_name', 'quantity', 'unit_price', 'subtotal']
    list_filter = ['sub_order__status', 'provider']
    search_fields = ['product_name', 'product_sku', 'sub_order__sub_order_number']
    readonly_fields = ['sub_order', 'product', 'provider', 'created_at']


@admin.register(PaymentProof)
class PaymentProofAdmin(admin.ModelAdmin):
    list_display = ['id', 'sub_order', 'payment_method', 'status', 'amount', 'uploaded_at', 'verified_by']
    list_filter = ['status', 'payment_method', 'uploaded_at', 'verified_at']
    search_fields = ['sub_order__sub_order_number', 'operation_number', 'external_transaction_id']
    readonly_fields = ['uploaded_by', 'uploaded_at', 'verified_by', 'verified_at']

    fieldsets = (
        ('Sub-Orden', {
            'fields': ('sub_order',)
        }),
        ('Información de Pago', {
            'fields': ('payment_method', 'amount', 'operation_number', 'file', 'external_transaction_id')
        }),
        ('Estado', {
            'fields': ('status', 'rejection_reason')
        }),
        ('Verificación', {
            'fields': ('verified_by', 'verified_at')
        }),
        ('Metadata', {
            'fields': ('uploaded_by', 'uploaded_at'),
            'classes': ('collapse',)
        }),
    )
