from django.db import migrations, models
import django.db.models.query_utils


class Migration(migrations.Migration):

    dependencies = [
        ('cart', '0001_initial'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='cart',
            constraint=models.UniqueConstraint(
                condition=django.db.models.query_utils.Q(('status', 'active'), ('user__isnull', False)),
                fields=['user'],
                name='unique_active_cart_per_user',
            ),
        ),
    ]
