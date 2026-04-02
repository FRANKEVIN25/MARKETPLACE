# Migration: add odoo_variante_id to VariantVehiculo for Odoo↔Django compatibility sync

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vehicles', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='variantvehiculo',
            name='odoo_variante_id',
            field=models.IntegerField(
                blank=True,
                null=True,
                unique=True,
                help_text=(
                    'ID de la variante en Odoo (vehiculo.variante). '
                    'Ancla para la sincronización de compatibilidades.'
                ),
            ),
        ),
    ]
