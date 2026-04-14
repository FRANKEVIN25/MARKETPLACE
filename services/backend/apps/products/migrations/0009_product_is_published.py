from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0008_drop_warehouse_stockitem_add_store'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='is_published',
            field=models.BooleanField(
                default=False,
                db_index=True,
                help_text='Visible públicamente en el marketplace. Un producto puede estar activo pero no publicado (ej: borrador).',
            ),
        ),
    ]
