from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_replace_imagefield_with_url_cloudinary'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='image_url_2',
            field=models.URLField(
                blank=True,
                max_length=500,
                null=True,
                help_text='Segunda imagen del producto (Cloudinary/CDN)'
            ),
        ),
        migrations.AddField(
            model_name='product',
            name='image_cloudinary_id_2',
            field=models.CharField(
                blank=True,
                max_length=200,
                null=True,
                help_text='Public ID en Cloudinary de la segunda imagen'
            ),
        ),
        migrations.AddField(
            model_name='product',
            name='image_url_3',
            field=models.URLField(
                blank=True,
                max_length=500,
                null=True,
                help_text='Tercera imagen del producto (Cloudinary/CDN)'
            ),
        ),
        migrations.AddField(
            model_name='product',
            name='image_cloudinary_id_3',
            field=models.CharField(
                blank=True,
                max_length=200,
                null=True,
                help_text='Public ID en Cloudinary de la tercera imagen'
            ),
        ),
    ]
