"""
Admin de Marketplace
"""
import logging
from django.contrib import admin
from django.contrib import messages
from .models import Provider, Member, ProviderReview

logger = logging.getLogger(__name__)


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'tier', 'rating_average', 'rating_count', 'is_approved', 'is_active', 'has_odoo_credentials', 'get_variantes_count', 'created_at']
    list_filter = ['is_approved', 'is_active', 'tier', 'created_at']
    search_fields = ['name', 'ruc', 'email']
    readonly_fields = ['slug', 'odoo_company_id', 'odoo_user_id', 'odoo_username', 'rating_average', 'rating_count', 'rating_breakdown', 'created_at', 'updated_at']
    filter_horizontal = ('variantes_habilitadas',)
    actions = ['aprobar_y_configurar_odoo', 'push_variantes_a_odoo']

    fieldsets = (
        ('Información Básica', {'fields': ('name', 'slug', 'logo', 'owner', 'tier')}),
        ('Contenido Público', {'fields': ('short_description', 'long_description')}),
        ('Datos de Negocio', {'fields': ('ruc', 'email', 'phone')}),
        ('Integración Odoo', {'fields': ('odoo_company_id', 'odoo_user_id', 'odoo_username')}),
        ('Reputación', {'fields': ('rating_average', 'rating_count', 'rating_breakdown')}),
        ('Estado', {'fields': ('is_active', 'is_approved')}),
        ('💳 Datos de Pago', {
            'fields': ('banco_nombre', 'banco_cuenta', 'banco_cci', 'yape_numero', 'plin_numero'),
        }),
        ('🚗 Scope de Vehículos', {
            'fields': ('variantes_habilitadas',),
            'description': (
                'Selecciona las variantes de vehículo con las que trabaja este proveedor. '
                'Después de guardar, ejecuta la acción "Push variantes a Odoo" para que '
                'el proveedor las vea disponibles en su UI de Odoo.'
            ),
        }),
        ('Metadata', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    @admin.display(description='Variantes')
    def get_variantes_count(self, obj):
        return obj.variantes_habilitadas.count()

    @admin.action(description='✅ Aprobar y configurar en Odoo')
    def aprobar_y_configurar_odoo(self, request, queryset):
        """
        Acción unificada para aprobar y configurar providers en Odoo.

        Comportamiento según estado del provider:
        - Sin credenciales Odoo + no aprobado  → aprueba; la signal dispara la task Celery.
        - Sin credenciales Odoo + ya aprobado  → relanza directamente la task (falló antes).
        - Ya tiene credenciales Odoo           → sincroniza datos de la company (RUC, email,
                                                  teléfono, moneda PEN) sin recrear nada.
        """
        from apps.sync.tasks import create_provider_with_odoo_setup
        from apps.sync.connector import OdooConnector
        from django.utils.crypto import get_random_string

        for provider in queryset:
            if provider.has_odoo_credentials():
                # Proveedor ya configurado en Odoo → solo sincronizar datos
                odoo = OdooConnector()
                ok = odoo.update_company(
                    company_id=provider.odoo_company_id,
                    email=provider.email or None,
                    currency_code='PEN',
                    vat=provider.ruc or None,
                    phone=provider.phone or None,
                )
                if ok:
                    self.message_user(
                        request,
                        f"🔄 {provider.name} (company {provider.odoo_company_id}): datos sincronizados en Odoo.",
                        messages.SUCCESS,
                    )
                else:
                    self.message_user(
                        request,
                        f"❌ {provider.name}: error al sincronizar datos en Odoo. Revisa los logs.",
                        messages.ERROR,
                    )
                continue

            # Sin credenciales → necesita aprovisionamiento completo
            odoo_password = provider.get_odoo_password_temp()
            if not odoo_password:
                odoo_password = get_random_string(12)
                provider.set_odoo_password_temp(odoo_password)
                provider.save(update_fields=['odoo_password_temp'])
                logger.warning("⚠️ %s: sin contraseña temp, generada automáticamente", provider.name)

            if not provider.is_approved:
                # Aprobar → la signal post_save dispara la task automáticamente
                provider.is_approved = True
                provider.save(update_fields=['is_approved'])
                self.message_user(
                    request,
                    f"🚀 {provider.name}: aprobado. La configuración de Odoo fue encolada.",
                    messages.SUCCESS,
                )
            else:
                # Ya aprobado pero sin credenciales (task anterior falló) → relanzar
                provider_data = {
                    'name': provider.name,
                    'email': provider.email or '',
                    'phone': provider.phone or '',
                    'ruc': provider.ruc or '',
                    'tier': provider.tier,
                }
                task = create_provider_with_odoo_setup.delay(
                    user_id=provider.owner.id,
                    provider_data=provider_data,
                    odoo_password=odoo_password,
                )
                self.message_user(
                    request,
                    f"🔄 {provider.name}: ya aprobado pero sin cuenta Odoo. Task relanzada (ID: {task.id}).",
                    messages.SUCCESS,
                )

    @admin.action(description='🚗 Push variantes a Odoo (scope por proveedor)')
    def push_variantes_a_odoo(self, request, queryset):
        """
        Ejecuta push_vehicles --provider-id para cada proveedor seleccionado.
        Empuja las variantes_habilitadas de cada provider hacia su tenant de Odoo
        y actualiza el scope (company_ids) en vehiculo.variante.
        """
        from django.core.management import call_command
        from io import StringIO

        total_ok = 0
        total_err = 0

        for provider in queryset:
            if not provider.odoo_company_id:
                self.message_user(
                    request,
                    f"⚠️ {provider.name} no tiene odoo_company_id. Omitido.",
                    messages.WARNING
                )
                continue

            count = provider.variantes_habilitadas.count()
            if count == 0:
                self.message_user(
                    request,
                    f"ℹ️ {provider.name} no tiene variantes habilitadas asignadas. Omitido.",
                    messages.WARNING
                )
                continue

            try:
                out = StringIO()
                call_command(
                    'push_vehicles',
                    provider_id=provider.pk,
                    stdout=out,
                    stderr=out,
                )
                total_ok += 1
                self.message_user(
                    request,
                    f"✅ {provider.name}: {count} variante(s) empujada(s) a Odoo.",
                    messages.SUCCESS
                )
            except Exception as exc:
                total_err += 1
                logger.error(f"push_variantes_a_odoo error para {provider.name}: {exc}", exc_info=True)
                self.message_user(
                    request,
                    f"❌ {provider.name}: error durante push — {exc}",
                    messages.ERROR
                )

        if total_ok:
            self.message_user(
                request,
                f"🏁 Push completado: {total_ok} proveedor(es) OK, {total_err} con error(es).",
                messages.SUCCESS if total_err == 0 else messages.WARNING
            )


@admin.register(Member)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'provider', 'role', 'can_manage_products', 'joined_at']
    list_filter = ['role', 'provider', 'joined_at']
    readonly_fields = ['joined_at']
    fieldsets = (
        ('Membresía', {'fields': ('user', 'provider', 'role')}),
        ('Permisos', {'fields': ('can_manage_products', 'can_manage_prices', 'can_manage_stock', 'can_invite_users', 'can_sync_odoo')}),
        ('Metadata', {'fields': ('joined_at',), 'classes': ('collapse',)}),
    )


@admin.register(ProviderReview)
class ProviderReviewAdmin(admin.ModelAdmin):
    list_display = ['provider', 'customer', 'sub_order', 'rating', 'status', 'is_visible', 'is_verified_purchase', 'created_at']
    list_filter = ['status', 'is_visible', 'is_verified_purchase', 'rating', 'created_at']
    search_fields = ['provider__name', 'customer__user__username', 'customer__company_name', 'sub_order__sub_order_number', 'comment']
    readonly_fields = ['provider', 'customer', 'sub_order', 'is_verified_purchase', 'created_at', 'updated_at']
