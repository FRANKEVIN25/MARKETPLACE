from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0009_provider_reviews_and_rating_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='provider',
            name='logo',
            field=models.ImageField(blank=True, help_text='Logo público del proveedor', null=True, upload_to='providers/logos/'),
        ),
    ]
