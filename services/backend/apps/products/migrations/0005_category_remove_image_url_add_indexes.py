# Generated 2026-04-08
# 
# Cambios sobre Category:
#   - Elimina el campo image_url (no se usa; imágenes de categoría se gestionarán
#     por otra vía cuando sea necesario).
#   - Agrega índices sobre is_active y parent_id para acelerar filtros frecuentes
#     en catálogos y árboles MPTT.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0004_product_autopart_quality_product_autopart_side'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='category',
            name='image_url',
        ),
        migrations.AddIndex(
            model_name='category',
            index=models.Index(fields=['is_active'], name='products_ca_is_acti_idx'),
        ),
        migrations.AddIndex(
            model_name='category',
            index=models.Index(fields=['parent_id'], name='products_ca_parent_idx'),
        ),
    ]
