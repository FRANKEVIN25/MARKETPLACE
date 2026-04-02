"""
Configuración del Admin para Customer
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count
from .models import Customer, Address, CustomerStats, CustomerProviderStats


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = [
        'customer_id',
        'get_name',
        'customer_type',
        'email',
        'phone',
        'document_display',
        'is_verified',
        'is_active',
        'total_orders_display',
        'created_at'
    ]
    
    list_filter = [
        'customer_type',
        'is_active',
        'is_verified',
        'document_type',
        'created_at'
    ]
    
    search_fields = [
        'customer_id',
        'user__username',
        'user__email',
        'user__first_name',
        'user__last_name',
        'company_name',
        'document_number',
        'phone'
    ]
    
    readonly_fields = [
        'customer_id',
        'created_at',
        'updated_at',
        'last_order_date'
    ]
    
    fieldsets = (
        ('Información Básica', {
            'fields': (
                'user',
                'customer_id',
                'customer_type',
                'phone'
            )
        }),
        ('Documentos', {
            'fields': (
                'document_type',
                'document_number'
            )
        }),
        ('Información de Empresa', {
            'fields': (
                'company_name',
                'business_activity'
            ),
            'classes': ('collapse',)
        }),
        ('Preferencias', {
            'fields': (
                'receive_newsletter',
                'receive_promotions'
            )
        }),
        ('Estado', {
            'fields': (
                'is_active',
                'is_verified'
            )
        }),
        ('Metadata', {
            'fields': (
                'created_at',
                'updated_at',
                'last_order_date'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def get_name(self, obj):
        """Nombre del cliente"""
        return obj.get_full_name()
    get_name.short_description = 'Nombre'
    
    def email(self, obj):
        """Email del usuario"""
        return obj.user.email
    email.short_description = 'Email'
    
    def document_display(self, obj):
        """Documento formateado"""
        if obj.document_number:
            return f"{obj.document_type}: {obj.document_number}"
        return "-"
    document_display.short_description = 'Documento'
    
    def total_orders_display(self, obj):
        """Total de órdenes"""
        if hasattr(obj, 'stats'):
            return obj.stats.total_orders
        return 0
    total_orders_display.short_description = 'Órdenes'
    
    def get_queryset(self, request):
        """Optimizar queries"""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'stats')


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = [
        'address_id',
        'customer_name',
        'address_type',
        'contact_name',
        'contact_phone',
        'location',
        'is_default',
        'created_at'
    ]
    
    list_filter = [
        'address_type',
        'is_default',
        'state',
        'city',
        'created_at'
    ]
    
    search_fields = [
        'address_id',
        'customer__customer_id',
        'customer__user__email',
        'contact_name',
        'contact_phone',
        'street',
        'district',
        'city',
        'agency_name'
    ]
    
    readonly_fields = [
        'address_id',
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('Cliente', {
            'fields': ('customer',)
        }),
        ('Identificación', {
            'fields': (
                'address_id',
                'address_type'
            )
        }),
        ('Contacto', {
            'fields': (
                'contact_name',
                'contact_phone'
            )
        }),
        ('Dirección', {
            'fields': (
                'street',
                'street_number',
                'apartment',
                'district',
                'city',
                'state',
                'postal_code',
                'country'
            )
        }),
        ('Agencia (si aplica)', {
            'fields': ('agency_name',),
            'classes': ('collapse',)
        }),
        ('Configuración', {
            'fields': (
                'is_default',
                'reference'
            )
        }),
        ('Metadata', {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def customer_name(self, obj):
        """Nombre del cliente"""
        return obj.customer.get_full_name()
    customer_name.short_description = 'Cliente'
    
    def location(self, obj):
        """Ubicación resumida"""
        return f"{obj.district}, {obj.city}"
    location.short_description = 'Ubicación'
    
    def get_queryset(self, request):
        """Optimizar queries"""
        qs = super().get_queryset(request)
        return qs.select_related('customer', 'customer__user')


@admin.register(CustomerStats)
class CustomerStatsAdmin(admin.ModelAdmin):
    list_display = [
        'customer_name',
        'total_orders',
        'total_spent_display',
        'average_order_display',
        'updated_at',
    ]

    search_fields = [
        'customer__customer_id',
        'customer__user__email',
        'customer__user__first_name',
        'customer__user__last_name',
    ]

    readonly_fields = [
        'customer',
        'total_orders',
        'total_spent',
        'average_order_value',
        'ver_historial_por_proveedor',
        'created_at',
        'updated_at',
    ]

    fieldsets = (
        ('Cliente', {
            'fields': ('customer',),
        }),
        ('Estadísticas Globales', {
            'description': 'Totales a través de todos los proveedores. '
                           'Se actualizan automáticamente al confirmar un pedido.',
            'fields': (
                'total_orders',
                'total_spent',
                'average_order_value',
            ),
        }),
        ('Detalle por Proveedor', {
            'fields': ('ver_historial_por_proveedor',),
        }),
        ('Información Adicional', {
            'fields': ('preferred_brands', 'notes'),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def customer_name(self, obj):
        return obj.customer.get_full_name()
    customer_name.short_description = 'Cliente'

    def total_spent_display(self, obj):
        return f'S/ {obj.total_spent:,.2f}'
    total_spent_display.short_description = 'Total Gastado'
    total_spent_display.admin_order_field = 'total_spent'

    def average_order_display(self, obj):
        return f'S/ {obj.average_order_value:,.2f}'
    average_order_display.short_description = 'Promedio por Orden'

    def ver_historial_por_proveedor(self, obj):
        """Tabla desde CustomerProviderStats (ya calculada, sin queries extra)."""
        rows = obj.customer.provider_stats.select_related('provider').order_by('-total_spent')
        if not rows:
            return '— Sin historial por proveedor. Se registra al confirmar un pedido. —'

        header = (
            '<table style="border-collapse:collapse;width:100%">'
            '<thead><tr>'
            '<th style="text-align:left;padding:4px 8px;border-bottom:1px solid #ccc">Proveedor</th>'
            '<th style="text-align:right;padding:4px 8px;border-bottom:1px solid #ccc">Pedidos</th>'
            '<th style="text-align:right;padding:4px 8px;border-bottom:1px solid #ccc">Total Gastado</th>'
            '<th style="text-align:right;padding:4px 8px;border-bottom:1px solid #ccc">Historial Ponderado</th>'
            '<th style="text-align:right;padding:4px 8px;border-bottom:1px solid #ccc">Descuento Actual</th>'
            '<th style="text-align:right;padding:4px 8px;border-bottom:1px solid #ccc">Falta para Tier</th>'
            '</tr></thead><tbody>'
        )
        body = ''
        for r in rows:
            next_tier = f'S/ {r.next_tier_amount:,.2f}' if r.next_tier_amount else '✓ Máximo'
            discount = f'{r.current_discount_percent} %' if r.current_discount_percent else '—'
            body += (
                f'<tr>'
                f'<td style="padding:4px 8px">{r.provider.name}</td>'
                f'<td style="text-align:right;padding:4px 8px">{r.total_orders}</td>'
                f'<td style="text-align:right;padding:4px 8px">S/ {r.total_spent:,.2f}</td>'
                f'<td style="text-align:right;padding:4px 8px">S/ {r.weighted_history:,.2f}</td>'
                f'<td style="text-align:right;padding:4px 8px;color:#16a34a;font-weight:bold">{discount}</td>'
                f'<td style="text-align:right;padding:4px 8px">{next_tier}</td>'
                f'</tr>'
            )
        return format_html(header + body + '</tbody></table>')
    ver_historial_por_proveedor.short_description = 'Historial por Proveedor (con descuentos)'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('customer', 'customer__user')


@admin.register(CustomerProviderStats)
class CustomerProviderStatsAdmin(admin.ModelAdmin):
    list_display = [
        'customer_display',
        'provider_display',
        'total_orders',
        'total_spent_display',
        'weighted_history_display',
        'current_discount_display',
        'next_tier_display',
        'last_recalculated',
    ]
    list_filter = ['provider', 'current_discount_percent']
    search_fields = [
        'customer__user__email',
        'customer__user__first_name',
        'customer__user__last_name',
        'customer__company_name',
        'provider__name',
    ]
    readonly_fields = [
        'customer', 'provider',
        'total_spent', 'total_orders',
        'weighted_history', 'current_discount_percent',
        'next_tier_amount', 'last_recalculated',
    ]
    ordering = ['-total_spent']

    def customer_display(self, obj):
        return obj.customer.get_full_name()
    customer_display.short_description = 'Cliente'
    customer_display.admin_order_field = 'customer__user__first_name'

    def provider_display(self, obj):
        return obj.provider.name
    provider_display.short_description = 'Proveedor'
    provider_display.admin_order_field = 'provider__name'

    def total_spent_display(self, obj):
        return f'S/ {obj.total_spent:,.2f}'
    total_spent_display.short_description = 'Total Gastado'
    total_spent_display.admin_order_field = 'total_spent'

    def weighted_history_display(self, obj):
        return f'S/ {obj.weighted_history:,.2f}'
    weighted_history_display.short_description = 'Historial Ponderado'
    weighted_history_display.admin_order_field = 'weighted_history'

    def current_discount_display(self, obj):
        if obj.current_discount_percent > 0:
            return format_html(
                '<span style="color:#16a34a;font-weight:bold">{} %</span>',
                obj.current_discount_percent,
            )
        return '—'
    current_discount_display.short_description = 'Descuento Actual'
    current_discount_display.admin_order_field = 'current_discount_percent'

    def next_tier_display(self, obj):
        if obj.next_tier_amount == 0:
            return format_html('<span style="color:#16a34a">Tier máximo ✓</span>')
        return f'Faltan S/ {obj.next_tier_amount:,.2f}'
    next_tier_display.short_description = 'Siguiente Tier'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'customer', 'customer__user', 'provider'
        )


# Personalización del Admin Site
admin.site.site_header = "ECOMPARTS - Marketplace"
admin.site.site_title = "ECOMPARTS Admin"
admin.site.index_title = "Panel de Administración"