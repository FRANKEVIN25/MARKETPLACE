from django.contrib import admin
from .models import DiscountRule


@admin.register(DiscountRule)
class DiscountRuleAdmin(admin.ModelAdmin):
    list_display = [
        'customer_type',
        'provider_display',
        'min_amount_display',
        'discount_percent_display',
        'is_active',
        'updated_at',
    ]
    list_filter = [
        'customer_type',
        'is_active',
        'provider',
    ]
    search_fields = [
        'provider__name',
    ]
    list_editable = ['is_active']
    ordering = ['customer_type', 'provider', 'min_amount']

    fieldsets = (
        ('Alcance', {
            'fields': ('customer_type', 'provider'),
            'description': (
                'Si "Proveedor" queda vacío, la regla actúa como fallback global '
                'para ese tipo de cliente.'
            ),
        }),
        ('Umbral y Descuento', {
            'fields': ('min_amount', 'discount_percent'),
        }),
        ('Estado', {
            'fields': ('is_active',),
        }),
    )

    def provider_display(self, obj):
        return obj.provider.name if obj.provider_id else '— Global —'
    provider_display.short_description = 'Proveedor'
    provider_display.admin_order_field = 'provider__name'

    def min_amount_display(self, obj):
        return f'S/ {obj.min_amount:,.2f}'
    min_amount_display.short_description = 'Monto Mínimo'
    min_amount_display.admin_order_field = 'min_amount'

    def discount_percent_display(self, obj):
        return f'{obj.discount_percent} %'
    discount_percent_display.short_description = 'Descuento'
    discount_percent_display.admin_order_field = 'discount_percent'
