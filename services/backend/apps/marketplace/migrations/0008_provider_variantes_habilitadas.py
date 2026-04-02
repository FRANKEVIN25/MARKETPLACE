"""
Migración: añade la relación M2M Provider.variantes_habilitadas → VariantVehiculo.
Esta tabla intermedia controla qué variantes de vehículo puede ver/usar
cada proveedor en su tenant de Odoo.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0007_add_odoo_password_temp'),
        ('vehicles', '0002_variantvehiculo_odoo_variante_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='provider',
            name='variantes_habilitadas',
            field=models.ManyToManyField(
                blank=True,
                help_text=(
                    "Variantes con las que trabaja este proveedor. "
                    "push_vehicles --provider-id solo empuja estas variantes al tenant "
                    "Odoo del proveedor y gestiona automáticamente la visibilidad."
                ),
                related_name='providers_habilitados',
                to='vehicles.variantvehiculo',
                verbose_name='Variantes de vehículos habilitadas',
            ),
        ),
    ]
