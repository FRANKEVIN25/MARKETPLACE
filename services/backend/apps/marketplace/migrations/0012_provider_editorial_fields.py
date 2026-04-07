from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0011_merge_20260407_0001'),
    ]

    operations = [
        migrations.AddField(
            model_name='provider',
            name='long_description',
            field=models.TextField(blank=True, help_text='Descripción editorial extendida para la página pública del proveedor'),
        ),
        migrations.AddField(
            model_name='provider',
            name='short_description',
            field=models.CharField(blank=True, help_text='Resumen corto visible en cards y cabeceras del proveedor', max_length=180),
        ),
    ]
