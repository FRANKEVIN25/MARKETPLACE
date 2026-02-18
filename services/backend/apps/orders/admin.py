"""
Admin para modelos de Orders
"""
from django.contrib import admin
from .models import Order, SubOrder, OrderItem, PaymentProof


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product_name', 'product_sku', 'quantity', 'unit_price', 'igv_rate', 'igv_amount', 'subtotal']
    can_delete = False


class SubOrderInline(admin.TabularInline):
    model = SubOrder
    extra = 0
    readonly_fields = ['sub_order_number', 'provider', 'status', 'subtotal', 'igv_amount', 'total']
    fields = ['sub_order_number', 'provider', 'status', 'subtotal', 'igv_amount', 'total']
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'customer', 'status', 'total', 'created_at']
    list_filter = ['status', 'delivery_method', 'created_at']
    search_fields = ['order_number', 'customer__user__email', 'customer__user__first_name']
    readonly_fields = ['order_number', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('order_number', 'customer', 'status')
        }),
        ('Entrega', {
            'fields': ('delivery_method', 'shipping_address')
        }),
        ('Montos', {
            'fields': ('subtotal', 'discount', 'tax', 'total')
        }),
        ('Notas', {
            'fields': ('customer_notes',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [SubOrderInline, OrderItemInline]


class PaymentProofInline(admin.TabularInline):
    model = PaymentProof
    extra = 0
    readonly_fields = ['payment_method', 'file', 'amount', 'uploaded_by', 'uploaded_at']
    can_delete = False


@admin.register(SubOrder)
class SubOrderAdmin(admin.ModelAdmin):
    list_display = ['sub_order_number', 'provider', 'status', 'total', 'created_at']
    list_filter = ['status', 'provider', 'created_at']
    search_fields = ['sub_order_number', 'order__order_number', 'provider__name']
    readonly_fields = ['sub_order_number', 'order', 'provider', 'created_at', 'updated_at', 'confirmed_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('sub_order_number', 'order', 'provider', 'status')
        }),
        ('Montos', {
            'fields': ('subtotal', 'igv_rate', 'igv_amount', 'total')
        }),
        ('Integración Odoo', {
            'fields': ('odoo_sale_id', 'odoo_invoice_id')
        }),
        ('Tracking', {
            'fields': ('tracking_number',)
        }),
        ('Rechazo', {
            'fields': ('rejection_reason',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'confirmed_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [PaymentProofInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'product_name', 'quantity', 'unit_price', 'subtotal']
    list_filter = ['order__status', 'provider']
    search_fields = ['product_name', 'product_sku', 'order__order_number']
    readonly_fields = ['order', 'sub_order', 'product', 'provider', 'created_at']


@admin.register(PaymentProof)
class PaymentProofAdmin(admin.ModelAdmin):
    list_display = ['id', 'sub_order', 'payment_method', 'amount', 'uploaded_at', 'verified_by']
    list_filter = ['payment_method', 'uploaded_at', 'verified_at']
    search_fields = ['sub_order__sub_order_number', 'operation_number']
    readonly_fields = ['uploaded_by', 'uploaded_at', 'verified_by', 'verified_at']
    
    fieldsets = (
        ('Sub-Orden', {
            'fields': ('sub_order',)
        }),
        ('Información de Pago', {
            'fields': ('payment_method', 'amount', 'operation_number', 'file')
        }),
        ('Verificación', {
            'fields': ('verified_by', 'verified_at', 'verification_notes')
        }),
        ('Metadata', {
            'fields': ('uploaded_by', 'uploaded_at'),
            'classes': ('collapse',)
        }),
    )
