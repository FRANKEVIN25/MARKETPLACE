"""
Admin para modelos de Orders
"""
from django.contrib import admin
from .models import Order, SupplierOrder, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['name', 'sku', 'quantity', 'unit_price', 'tax_percent', 'tax_amount', 'total_price']
    can_delete = False


class SupplierOrderInline(admin.TabularInline):
    model = SupplierOrder
    extra = 0
    readonly_fields = ['provider', 'status', 'subtotal', 'tax_amount', 'total']
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'customer', 'status', 'total', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order_number', 'customer__user__email']
    readonly_fields = ['order_number', 'created_at', 'updated_at']
    inlines = [SupplierOrderInline]


@admin.register(SupplierOrder)
class SupplierOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'provider', 'status', 'total', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order__order_number', 'provider__name']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'supplier_order', 'name', 'sku', 'quantity', 'unit_price', 'total_price']
    list_filter = ['supplier_order__status']
    search_fields = ['name', 'sku', 'supplier_order__order__order_number']
    readonly_fields = ['created_at', 'updated_at']
