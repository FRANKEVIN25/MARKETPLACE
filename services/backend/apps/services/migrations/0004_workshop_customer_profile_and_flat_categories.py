from django.db import migrations, models
import django.db.models.deletion


def forwards(apps, schema_editor):
    db_alias = schema_editor.connection.alias

    Workshop = apps.get_model('services', 'Workshop')
    Service = apps.get_model('services', 'Service')
    ServiceCategory = apps.get_model('services', 'ServiceCategory')
    Customer = apps.get_model('customer', 'Customer')
    CustomerStats = apps.get_model('customer', 'CustomerStats')

    # 1. Aplanar categorías existentes: los servicios quedan apuntando a la
    # categoría raíz y las especialidades del taller también.
    for service in Service.objects.using(db_alias).all():
        category = ServiceCategory.objects.using(db_alias).filter(pk=service.category_id).first()
        if category and getattr(category, 'parent_id', None):
            service.category_id = category.parent_id
            service.save(update_fields=['category'])

    specialties_through = Workshop.specialties.through
    for rel in specialties_through.objects.using(db_alias).all():
        category = ServiceCategory.objects.using(db_alias).filter(pk=rel.servicecategory_id).first()
        if category and getattr(category, 'parent_id', None):
            specialties_through.objects.using(db_alias).get_or_create(
                workshop_id=rel.workshop_id,
                servicecategory_id=category.parent_id,
            )
            specialties_through.objects.using(db_alias).filter(pk=rel.pk).delete()

    ServiceCategory.objects.using(db_alias).filter(parent__isnull=False).delete()

    # 2. Garantizar Customer(company) + Stats para cada taller existente.
    for workshop in Workshop.objects.using(db_alias).all():
        customer = Customer.objects.using(db_alias).filter(user_id=workshop.owner_id).first()

        if customer is None:
            customer = Customer.objects.using(db_alias).create(
                user_id=workshop.owner_id,
                customer_type='company',
                company_name=workshop.name,
                document_type='RUC',
                document_number=workshop.ruc or '',
                phone=workshop.phone or '',
            )
        else:
            changed = []
            if customer.customer_type != 'company':
                customer.customer_type = 'company'
                changed.append('customer_type')
            if customer.company_name != workshop.name:
                customer.company_name = workshop.name
                changed.append('company_name')
            if customer.document_type != 'RUC':
                customer.document_type = 'RUC'
                changed.append('document_type')
            if workshop.ruc and customer.document_number != workshop.ruc:
                customer.document_number = workshop.ruc
                changed.append('document_number')
            if workshop.phone and customer.phone != workshop.phone:
                customer.phone = workshop.phone
                changed.append('phone')
            if changed:
                customer.save(update_fields=changed)

        CustomerStats.objects.using(db_alias).get_or_create(customer_id=customer.id)

        if workshop.customer_profile_id != customer.id:
            Workshop.objects.using(db_alias).filter(pk=workshop.pk).update(
                customer_profile_id=customer.id,
            )


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('customer', '0001_initial'),
        ('services', '0003_workshopvehicleexpertise_last_job_date_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='workshop',
            name='customer_profile',
            field=models.OneToOneField(blank=True, help_text='Perfil Customer empresa asociado al taller. Conserva historial y beneficios del marketplace.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='workshop', to='customer.customer'),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='workshop',
            name='is_formal',
        ),
        migrations.RemoveField(
            model_name='servicecategory',
            name='parent',
        ),
    ]
