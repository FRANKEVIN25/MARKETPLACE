from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_category_odoo_id'),
        ('products', '0002_replace_imagefield_with_url_cloudinary'),
    ]

    operations = []