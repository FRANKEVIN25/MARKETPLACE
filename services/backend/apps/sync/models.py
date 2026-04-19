from django.db import models


class ProviderSyncState(models.Model):
    SYNC_TYPE_CHOICES = [
        ('catalog', 'Catalog Snapshot'),
        ('images', 'Images'),
        ('stock', 'Stock'),
        ('compatibility', 'Compatibility'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('partial', 'Partial'),
        ('failed', 'Failed'),
    ]

    provider = models.ForeignKey(
        'marketplace.Provider',
        on_delete=models.CASCADE,
        related_name='sync_states',
    )
    sync_type = models.CharField(max_length=20, choices=SYNC_TYPE_CHOICES)
    last_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    last_started_at = models.DateTimeField(null=True, blank=True)
    last_finished_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_duration_seconds = models.FloatField(null=True, blank=True)
    last_error = models.TextField(blank=True, default='')
    last_metrics = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sync_provider_sync_state'
        constraints = [
            models.UniqueConstraint(
                fields=['provider', 'sync_type'],
                name='unique_provider_sync_type',
            )
        ]
        indexes = [
            models.Index(fields=['provider', 'sync_type']),
            models.Index(fields=['sync_type', 'last_status']),
        ]

    def __str__(self):
        return f"{self.provider_id}:{self.sync_type}:{self.last_status}"