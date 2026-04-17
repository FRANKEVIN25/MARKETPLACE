from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0011_product_odoo_image_version'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['provider', 'odoo_template_id'], name='products_pr_provide_oodotmpl_idx'),
        ),
    ]