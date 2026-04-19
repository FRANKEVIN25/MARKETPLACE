from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.customer.models import Customer, CustomerStats
from apps.services.models import Workshop
from .models import WorkshopReview, WorkshopServiceHistory

@receiver(post_save, sender=Workshop)
def ensure_workshop_customer_profile(sender, instance, **kwargs):
    """
    Garantiza que todo taller tenga un Customer(company) ligado al mismo owner.

    Si el usuario ya tenía historial como Customer, se reutiliza el mismo perfil
    y se actualiza a tipo company para preservar beneficios, direcciones y stats.
    """
    customer, _ = Customer.objects.get_or_create(
        user=instance.owner,
        defaults={
            'customer_type': 'company',
            'company_name': instance.name,
            'document_type': 'RUC',
            'document_number': instance.ruc or '',
            'phone': instance.phone,
        },
    )

    update_fields = []

    if customer.customer_type != 'company':
        customer.customer_type = 'company'
        update_fields.append('customer_type')

    if customer.company_name != instance.name:
        customer.company_name = instance.name
        update_fields.append('company_name')

    if customer.document_type != 'RUC':
        customer.document_type = 'RUC'
        update_fields.append('document_type')

    if instance.ruc and customer.document_number != instance.ruc:
        customer.document_number = instance.ruc
        update_fields.append('document_number')

    if instance.phone and customer.phone != instance.phone:
        customer.phone = instance.phone
        update_fields.append('phone')

    if update_fields:
        customer.save(update_fields=update_fields)

    CustomerStats.objects.get_or_create(customer=customer)

    if instance.customer_profile_id != customer.id:
        Workshop.objects.filter(pk=instance.pk).update(customer_profile=customer)



@receiver(post_save, sender=WorkshopReview)
def update_service_history_rating(sender, instance, created, **kwargs):
    """
    Recalcula avg_rating y total_ratings en WorkshopServiceHistory cada vez
    que se crea una reseña con servicio asociado.

    Se recalcula desde la fuente (agregación SQL) en lugar de usar fórmula
    incremental, para evitar condiciones de carrera cuando dos reseñas se
    guardan simultáneamente para el mismo taller+servicio.
    """
    if not (created and instance.service):
        return

    from django.db.models import Avg, Count

    agg = WorkshopReview.objects.filter(
        workshop=instance.workshop,
        service=instance.service,
    ).aggregate(avg=Avg('rating'), total=Count('id'))

    WorkshopServiceHistory.objects.update_or_create(
        workshop=instance.workshop,
        service=instance.service,
        defaults={
            'avg_rating': agg['avg'] or 0,
            'total_ratings': agg['total'],
        },
    )