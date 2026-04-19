from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('marketplace', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProviderSyncState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sync_type', models.CharField(choices=[('catalog', 'Catalog Snapshot'), ('images', 'Images'), ('stock', 'Stock'), ('compatibility', 'Compatibility')], max_length=20)),
                ('last_status', models.CharField(choices=[('pending', 'Pending'), ('running', 'Running'), ('success', 'Success'), ('partial', 'Partial'), ('failed', 'Failed')], db_index=True, default='pending', max_length=20)),
                ('last_started_at', models.DateTimeField(blank=True, null=True)),
                ('last_finished_at', models.DateTimeField(blank=True, null=True)),
                ('last_success_at', models.DateTimeField(blank=True, null=True)),
                ('last_duration_seconds', models.FloatField(blank=True, null=True)),
                ('last_error', models.TextField(blank=True, default='')),
                ('last_metrics', models.JSONField(blank=True, default=dict)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('provider', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='sync_states', to='marketplace.provider')),
            ],
            options={
                'db_table': 'sync_provider_sync_state',
            },
        ),
        migrations.AddConstraint(
            model_name='providersyncstate',
            constraint=models.UniqueConstraint(fields=('provider', 'sync_type'), name='unique_provider_sync_type'),
        ),
        migrations.AddIndex(
            model_name='providersyncstate',
            index=models.Index(fields=['provider', 'sync_type'], name='sync_provid_provide_17e4a6_idx'),
        ),
        migrations.AddIndex(
            model_name='providersyncstate',
            index=models.Index(fields=['sync_type', 'last_status'], name='sync_provid_sync_ty_a10c07_idx'),
        ),
    ]