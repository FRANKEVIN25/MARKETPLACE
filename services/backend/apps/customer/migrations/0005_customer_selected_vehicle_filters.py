from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vehicles', '0002_variantvehiculo_odoo_variante_id'),
        ('customer', '0004_add_customer_provider_stats'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='selected_vehicle_marca',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='customers_with_selected_marca', to='vehicles.marca', verbose_name='Marca seleccionada'),
        ),
        migrations.AddField(
            model_name='customer',
            name='selected_vehicle_modelo',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='customers_with_selected_modelo', to='vehicles.modelovehiculo', verbose_name='Modelo seleccionado'),
        ),
        migrations.AddField(
            model_name='customer',
            name='selected_vehicle_variante',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='customers_with_selected_variante', to='vehicles.variantvehiculo', verbose_name='Variante seleccionada'),
        ),
    ]