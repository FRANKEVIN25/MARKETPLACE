from django.db import models
from decimal import Decimal


class DiscountRule(models.Model):
    """
    Define niveles de descuento según el tipo de cliente, el proveedor y el importe
    acumulado del historial de compras cliente-proveedor.

    - Si `provider` es null, la regla aplica como fallback global para ese tipo de cliente.
    - Si `provider` tiene valor, la regla aplica solo para ese proveedor específico.
    El motor de descuentos siempre prioriza la regla de proveedor específico sobre la global.
    """

    CUSTOMER_TYPE_CHOICES = [
        ('individual', 'Individual'),
        ('company', 'Company'),
    ]

    customer_type = models.CharField(
        max_length=20,
        choices=CUSTOMER_TYPE_CHOICES,
    )

    provider = models.ForeignKey(
        'marketplace.Provider',
        on_delete=models.CASCADE,
        related_name='discount_rules',
        null=True,
        blank=True,
        help_text="Proveedor al que aplica esta regla. Null = regla global (fallback)."
    )

    min_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Monto acumulado mínimo (historial cliente-proveedor) para activar este descuento"
    )

    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Porcentaje de descuento (ej. 5.00 = 5%)"
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['customer_type', 'provider', 'min_amount']
        indexes = [
            models.Index(fields=['customer_type', 'provider', 'min_amount', 'is_active']),
        ]

    def __str__(self):
        provider_label = self.provider.name if self.provider_id else 'global'
        return f"{self.customer_type} / {provider_label} ≥ {self.min_amount} → {self.discount_percent}%"

  


# no es necesario para el PMV
"""
class Coupon(models.Model):
    PERCENT = 'percent'
    FIXED = 'fixed'

    TYPE_CHOICES = [
        (PERCENT, 'Percentage'),
        (FIXED, 'Fixed amount'),
    ]

    code = models.CharField(max_length=20, unique=True)
    discount_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    value = models.DecimalField(max_digits=10, decimal_places=2)

    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)

    max_uses = models.PositiveIntegerField(default=0)
    used_count = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code
 
 """