"""
Admin de Marketplace
"""
from django.contrib import admin
from .models import Provider, Member, ProviderMarca

class ProviderMarcaInline(admin.TabularInline):
    model = ProviderMarca
    extra = 1
    fields = ['marca', 'activo']


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'is_approved', 'is_active', 'get_members_count', 'created_at']
    list_filter = ['is_approved', 'is_active', 'created_at']
    search_fields = ['name', 'ruc', 'email']
    readonly_fields = ['slug', 'created_at', 'updated_at']
    inlines = [ProviderMarcaInline]
    fieldsets = (
        ('Información Básica', {'fields': ('name', 'slug', 'owner')}),
        ('Datos de Negocio', {'fields': ('ruc', 'email', 'phone')}),
        ('Integración Odoo', {'fields': ('odoo_company_id',)}),
        ('Estado', {'fields': ('is_active', 'is_approved')}),
        ('Metadata', {'fields': ('created_at', 'updated_at'),'classes': ('collapse',)}),
    )

@admin.register(Member)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'provider', 'role', 'can_manage_products', 'joined_at']
    list_filter = ['role', 'provider', 'joined_at']
    readonly_fields = ['joined_at']
    fieldsets = (
        ('Membresía', {'fields': ('user', 'provider', 'role')}),
        ('Permisos', {'fields': ('can_manage_products','can_manage_prices','can_manage_stock','can_invite_users','can_sync_odoo')}),
        ('Metadata', {'fields': ('joined_at',),'classes': ('collapse',)}),
    )