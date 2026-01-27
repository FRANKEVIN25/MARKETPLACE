from django.db import models
from decimal import Decimal

from django.db import models

class DiscountRule(models.Model):
    """
    Define niveles de descuento según el tipo de cliente y el importe total de la compra.
    Este modelo NO calcula precios. Solo describe las reglas de descuento.
    """

    CUSTOMER_TYPE_CHOICES = [
        ('individual', 'Individual'),
        ('company', 'Company'),
    ]

    customer_type = models.CharField(
        max_length=20,
        choices=CUSTOMER_TYPE_CHOICES,
    )

    min_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Minimum accumulated amount to apply this discount"
    )

    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Discount percentage (e.g. 5.00 = 5%)"
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['customer_type', 'min_amount']
        indexes = [
            models.Index(fields=['customer_type', 'min_amount', 'is_active']),
        ]

    def __str__(self):
        return f"{self.customer_type} ≥ {self.min_amount} → {self.discount_percent}%"

  

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
 