from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0010_services_model_fixes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='workshop',
            name='service_level',
            field=models.CharField(
                choices=[
                    ('BASIC', 'Básico — Sin ERP'),
                    ('MANAGED', 'Gestionado — Odoo ERP + Repair'),
                    ('ADVANCED', 'Avanzado — Odoo ERP + Repair + ecomp + analitica'),
                ],
                default='BASIC',
                help_text='Define qué tan sofisticada es la operación interna del taller.',
                max_length=10,
                verbose_name='Nivel de servicio (ERP)',
            ),
        ),
    ]