from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('customer', '0001_initial'),
        ('orders', '0007_add_discount_fields_to_suborder'),
        ('marketplace', '0008_provider_variantes_habilitadas'),
    ]

    operations = [
        migrations.AddField(
            model_name='provider',
            name='rating_average',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Calificación promedio visible del proveedor (0.00 - 5.00)', max_digits=3),
        ),
        migrations.AddField(
            model_name='provider',
            name='rating_breakdown',
            field=models.JSONField(blank=True, default=dict, help_text='Distribución de calificaciones visibles por estrella'),
        ),
        migrations.AddField(
            model_name='provider',
            name='rating_count',
            field=models.PositiveIntegerField(default=0, help_text='Cantidad total de reseñas visibles del proveedor'),
        ),
        migrations.CreateModel(
            name='ProviderReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.PositiveSmallIntegerField(choices=[(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)], help_text='Calificación del 1 al 5')),
                ('comment', models.TextField(blank=True, help_text='Comentario opcional del cliente sobre el proveedor')),
                ('is_verified_purchase', models.BooleanField(default=True, help_text='True cuando la reseña está asociada a una suborden del cliente')),
                ('is_visible', models.BooleanField(default=True, help_text='Permite ocultar la reseña sin eliminarla')),
                ('status', models.CharField(choices=[('published', 'Publicado'), ('pending', 'Pendiente de revisión'), ('hidden', 'Oculto')], default='published', help_text='Estado de moderación de la reseña', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='provider_reviews', to='customer.customer')),
                ('provider', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='marketplace.provider')),
                ('sub_order', models.ForeignKey(help_text='Suborden entregada asociada a esta reseña', on_delete=django.db.models.deletion.CASCADE, related_name='provider_reviews', to='orders.suborder')),
            ],
            options={
                'verbose_name': 'Reseña de Proveedor',
                'verbose_name_plural': 'Reseñas de Proveedores',
                'db_table': 'marketplace_provider_review',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='providerreview',
            index=models.Index(fields=['provider', 'status', 'is_visible'], name='marketplace_provide_provide_05d5c3_idx'),
        ),
        migrations.AddIndex(
            model_name='providerreview',
            index=models.Index(fields=['customer', 'created_at'], name='marketplace_provide_custome_d91460_idx'),
        ),
        migrations.AddIndex(
            model_name='providerreview',
            index=models.Index(fields=['sub_order'], name='marketplace_provide_sub_ord_89a6c2_idx'),
        ),
        migrations.AddConstraint(
            model_name='providerreview',
            constraint=models.UniqueConstraint(fields=('customer', 'sub_order'), name='unique_provider_review_per_customer_suborder'),
        ),
    ]
