from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0010_category_sync_key'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='odoo_image_version',
            field=models.CharField(
                blank=True,
                help_text='Versión remota usada para decidir si la imagen debe refrescarse desde Odoo.',
                max_length=64,
                null=True,
            ),
        ),
    ]