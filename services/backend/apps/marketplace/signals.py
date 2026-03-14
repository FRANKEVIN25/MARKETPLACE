"""
Signals de Marketplace
Detecta cambios en el modelo Provider y dispara tasks automáticamente
"""
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)


@receiver(pre_save, sender='marketplace.Provider')
def provider_pre_save(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._previous_is_approved = sender.objects.get(pk=instance.pk).is_approved
        except sender.DoesNotExist:
            instance._previous_is_approved = False
    else:
        instance._previous_is_approved = False


@receiver(post_save, sender='marketplace.Provider')
def provider_post_save(sender, instance, created, **kwargs):
    previous = getattr(instance, '_previous_is_approved', False)
    just_approved = not previous and instance.is_approved

    if just_approved and not instance.has_odoo_credentials():
        logger.info(f"🔔 Signal: Provider '{instance.name}' aprobado — iniciando setup Odoo automático")

        odoo_password = instance.get_odoo_password_temp()
        if not odoo_password:
            from django.utils.crypto import get_random_string
            odoo_password = get_random_string(12)
            logger.warning(f"⚠️ {instance.name}: sin contraseña temp, usando aleatoria")

        provider_data = {
            'name': instance.name,
            'email': instance.email or '',
            'phone': instance.phone or '',
            'ruc': instance.ruc or '',
            'tier': instance.tier,
        }

        from apps.sync.tasks import create_provider_with_odoo_setup
        task = create_provider_with_odoo_setup.delay(
            user_id=instance.owner.id,
            provider_data=provider_data,
            odoo_password=odoo_password,
        )
        logger.info(f"🚀 Task lanzada automáticamente para '{instance.name}': {task.id}")
