"""
Admin de Marketplace
"""
import logging
from django.contrib import admin
from django.contrib import messages
from .models import Provider, Member

logger = logging.getLogger(__name__)


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'tier', 'is_approved', 'is_active', 'has_odoo_credentials', 'get_variantes_count', 'created_at']
    list_filter = ['is_approved', 'is_active', 'tier', 'created_at']
    search_fields = ['name', 'ruc', 'email']
    readonly_fields = ['slug', 'odoo_company_id', 'odoo_user_id', 'odoo_username', 'created_at', 'updated_at']
    filter_horizontal = ('variantes_habilitadas',)
    actions = ['aprobar_y_configurar_odoo', 'solo_aprobar', 'push_variantes_a_odoo']

    fieldsets = (
        ('Información Básica', {'fields': ('name', 'slug', 'owner', 'tier')}),
        ('Datos de Negocio', {'fields': ('ruc', 'email', 'phone')}),
        ('Integración Odoo', {'fields': ('odoo_company_id', 'odoo_user_id', 'odoo_username')}),
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

    @admin.action(description='✅ Aprobar y configurar en Odoo (crea Company + Usuario)')
    def aprobar_y_configurar_odoo(self, request, queryset):
        """
        Aprueba los providers seleccionados Y dispara la Celery task
        que crea la Company + Usuario en Odoo con los permisos correctos.
        """
        from apps.sync.tasks import create_provider_with_odoo_setup

        for provider in queryset:
            if provider.has_odoo_credentials():
                self.message_user(
                    request,
                    f"⚠️ {provider.name} ya tiene credenciales de Odoo. Omitido.",
                    messages.WARNING
                )
                continue

            # Recuperar la contraseña Odoo que el vendor eligió durante el registro
            temp_password = provider.get_odoo_password_temp()
            if not temp_password:
                # Fallback: generar nueva contraseña si no hay temp guardada
                from django.utils.crypto import get_random_string
                temp_password = get_random_string(12)
                logger.warning(f"⚠️ {provider.name}: sin contraseña temp, usando aleatoria")

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
                odoo_password=temp_password,
            )

            # Marcar como aprobado
            provider.is_approved = True
            provider.save(update_fields=['is_approved'])

            self.message_user(
                request,
                f"🚀 {provider.name}: aprobado. Configurando Odoo en segundo plano (task: {task.id[:8]}...)",
                messages.SUCCESS
            )

    @admin.action(description='👍 Solo aprobar (sin configurar Odoo)')
    def solo_aprobar(self, request, queryset):
        """
        Aprueba los providers sin tocar Odoo.
        Útil para providers que ya tienen credenciales o para aprobar manualmente.
        """
        updated = queryset.update(is_approved=True)
        self.message_user(
            request,
            f"✅ {updated} proveedor(es) aprobado(s).",
            messages.SUCCESS
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
