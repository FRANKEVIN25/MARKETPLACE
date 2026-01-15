"""
Admin de Productos
"""
from mptt.admin import MPTTModelAdmin
from .models import Category, Product, CompatibilidadProducto
from django.contrib import admin
from apps.vehicles.services.provider_variants import variantes_disponibles_para_proveedor
from apps.marketplace.models import Member



def get_provider_from_request(request):
    try:
        return Member.objects.get(user=request.user).provider
    except Member.DoesNotExist:
        return None


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
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "variante":
            # Obtener el provider del contexto del producto padre
            provider = get_provider_from_request(request)
            if provider:
                kwargs["queryset"] = variantes_disponibles_para_proveedor(provider)
            else:
                kwargs["queryset"] = db_field.remote_field.model.objects.none()
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'reference',
        'provider',
        'price',
        'active',
        'es_universal',
        'is_synced',
        'created_at'
    ]
    list_filter = ['active', 'product_type', 'provider', 'category', 'created_at']
    search_fields = ['name', 'reference', 'manufacturer_code']
    readonly_fields = [
        'slug',
        'odoo_product_id',
        'odoo_template_id',
        'last_synced_at',
        'created_at',
        'updated_at'
    ]

    inlines = [CompatibilidadProductoInline]

    fieldsets = (
        ('Proveedor', {
            'fields': ('provider',)
        }),
        ('Información Básica', {
            'fields': ('name', 'reference', 'slug', 'product_type')
        }),
        ('Contenido', {
            'fields': ('description', 'image', 'manufacturer_code')
        }),
        ('Clasificación', {
            'fields': ('category',)
        }),
        ('Precio', {
            'fields': ('price',)
        }),
        ('Estado', {
            'fields': ('active',)
        }),
        ('Integración Odoo', {
            'fields': ('odoo_product_id', 'odoo_template_id', 'last_synced_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_synced(self, obj):
        return obj.is_synced
    
    is_synced.boolean = True
    is_synced.short_description = 'Sincronizado'


@admin.register(CompatibilidadProducto)
class CompatibilidadProductoAdmin(admin.ModelAdmin):
    list_display = ['producto', 'variante', 'notas_instalacion']
    list_filter = ['producto__provider']
    autocomplete_fields = ['producto', 'variante']
    search_fields = [
        'producto__name',
        'producto__reference',
        'variante__modelo__nombre',
        'variante__modelo__marca__nombre'
    ]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        provider = get_provider_from_request(request)
        if provider:
            return qs.filter(producto__provider=provider)
        return qs.none()
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        provider = get_provider_from_request(request)
        
        if db_field.name == "variante" and provider:
            kwargs["queryset"] = variantes_disponibles_para_proveedor(provider)
        
        if db_field.name == "producto" and provider:
            kwargs["queryset"] = Product.objects.filter(provider=provider)
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)