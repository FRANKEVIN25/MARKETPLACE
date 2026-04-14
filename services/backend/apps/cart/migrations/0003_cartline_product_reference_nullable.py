from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cart', '0002_unique_active_cart_per_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cartline',
            name='product_reference',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
