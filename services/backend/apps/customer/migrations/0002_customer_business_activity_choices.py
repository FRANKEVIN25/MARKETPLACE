from django.db import migrations, models


BUSINESS_ACTIVITY_CHOICES = [
    ('workshop', 'Taller mecánico'),
    ('parts_supplier', 'Proveedor de autopartes'),
    ('retail_store', 'Tienda de repuestos'),
    ('distributor', 'Distribuidor mayorista'),
    ('fleet', 'Flota o transporte'),
    ('dealer', 'Concesionario'),
    ('manufacturer', 'Fabricación o rectificación'),
    ('insurance', 'Aseguradora o peritaje'),
    ('other', 'Otro rubro automotriz'),
]


def normalize_business_activity(apps, schema_editor):
    Customer = apps.get_model('customer', 'Customer')

    for customer in Customer.objects.exclude(business_activity=''):
        raw_value = (customer.business_activity or '').strip().lower()

        if not raw_value:
            normalized = ''
        elif 'taller' in raw_value:
            normalized = 'workshop'
        elif any(term in raw_value for term in ['autoparte', 'autopartes', 'repuesto', 'repuestos', 'proveedor']):
            normalized = 'parts_supplier'
        elif any(term in raw_value for term in ['tienda', 'retail', 'mostrador']):
            normalized = 'retail_store'
        elif any(term in raw_value for term in ['distrib', 'mayorista']):
            normalized = 'distributor'
        elif any(term in raw_value for term in ['flota', 'transporte', 'logistica', 'logística']):
            normalized = 'fleet'
        elif any(term in raw_value for term in ['conces', 'dealer']):
            normalized = 'dealer'
        elif any(term in raw_value for term in ['fabric', 'rectific', 'manufact']):
            normalized = 'manufacturer'
        elif any(term in raw_value for term in ['aseg', 'perita']):
            normalized = 'insurance'
        else:
            normalized = 'other'

        if customer.business_activity != normalized:
            customer.business_activity = normalized
            customer.save(update_fields=['business_activity'])


class Migration(migrations.Migration):

    dependencies = [
        ('customer', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(normalize_business_activity, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='customer',
            name='business_activity',
            field=models.CharField(
                blank=True,
                choices=BUSINESS_ACTIVITY_CHOICES,
                max_length=40,
                verbose_name='Actividad Económica',
            ),
        ),
    ]