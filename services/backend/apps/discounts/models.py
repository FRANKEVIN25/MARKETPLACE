from django.db import models
from django.db.models import Q
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
            # Equality filters first (customer_type, provider, is_active), range/sort last (min_amount DESC).
            # El motor filtra con min_amount__lte y ordena por -min_amount, por lo que
            # el índice debe tener los campos de igualdad antes del campo de rango.
            models.Index(fields=['customer_type', 'provider', 'is_active', '-min_amount']),
        ]
        constraints = [
            # Unicidad para reglas de proveedor específico (provider NOT NULL).
            # Dos constraints separadas porque PostgreSQL trata NULL != NULL,
            # por lo que una sola UniqueConstraint no cubre las reglas globales.
            models.UniqueConstraint(
                fields=['customer_type', 'provider', 'min_amount'],
                condition=Q(provider__isnull=False),
                name='unique_discount_tier_per_provider',
            ),
            # Unicidad para reglas globales (provider NULL).
            models.UniqueConstraint(
                fields=['customer_type', 'min_amount'],
                condition=Q(provider__isnull=True),
                name='unique_discount_tier_global',
            ),
            # El descuento debe estar entre 0 % y 100 %.
            models.CheckConstraint(
                check=Q(discount_percent__gte=0) & Q(discount_percent__lte=100),
                name='valid_discount_range',
            ),
            # El monto mínimo no puede ser negativo.
            models.CheckConstraint(
                check=Q(min_amount__gte=0),
                name='min_amount_non_negative',
            ),
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