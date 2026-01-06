"""
Admin de Marketplace
"""
from django.contrib import admin
from .models import ProviderGroup, GroupMembership


@admin.register(ProviderGroup)
class ProviderGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'is_approved', 'is_active', 'get_members_count', 'created_at']
    list_filter = ['is_approved', 'is_active', 'created_at']
    search_fields = ['name', 'ruc', 'email']
    readonly_fields = ['slug', 'created_at', 'updated_at']
    fieldsets = (
        ('Información Básica', {'fields': ('name', 'slug', 'owner')}),
        ('Datos de Negocio', {'fields': ('ruc', 'email', 'phone')}),
        ('Integración Odoo', {'fields': ('odoo_company_id',)}),
        ('Estado', {'fields': ('is_active', 'is_approved')}),
        ('Metadata', {'fields': ('created_at', 'updated_at'),'classes': ('collapse',)}),
    )

@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'group', 'role', 'can_manage_products', 'joined_at']
    list_filter = ['role', 'group', 'joined_at']
    search_fields = ['user__username', 'user__email', 'group__name']
    readonly_fields = ['joined_at']
    fieldsets = (
        ('Membresía', {'fields': ('user', 'group', 'role')}),
        ('Permisos', {'fields': ('can_manage_products','can_manage_prices','can_manage_stock','can_invite_users','can_sync_odoo')}),
        ('Metadata', {'fields': ('joined_at',),'classes': ('collapse',)}),
    )