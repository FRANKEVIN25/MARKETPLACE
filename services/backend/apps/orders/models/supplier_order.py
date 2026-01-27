# orders/models/supplier_order.py
"""
SupplierOrder - Porción de una Order para un Proveedor específico.
"""

from django.db import models
from decimal import Decimal
from django.db.models import Sum


class SupplierOrder(models.Model):
    """
    Representa los items de una Order que pertenecen a UN proveedor (Provider).
    
    Permite dividir la orden por proveedor para:
    - Gestión independiente de pagos
    - Tracking por proveedor
    - Cumplimiento desde diferentes almacenes
    """

    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('confirmed', 'Confirmada'),
        ('processing', 'Procesando'),
        ('shipped', 'Enviada'),
        ('completed', 'Completada'),
        ('cancelled', 'Cancelada'),
    ]

    # Relación con la orden maestra
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='supplier_orders',
        verbose_name='Orden'
    )

    # Relación con el proveedor (Provider de Marketplace)
    provider = models.ForeignKey(
        'marketplace.Provider',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supplier_orders',
        verbose_name='Proveedor',
        help_text='Proveedor del marketplace que suministra estos items'
    )

    # Referencia a Odoo (legacy/sync)
    company_id = models.IntegerField(
        help_text="ID de la compañía en Odoo (si aplica)"
    )

    # Almacén de cumplimiento
    warehouse_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="ID del warehouse en Odoo para fulfillment"
    )

    # Estado
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Estado',
        db_index=True
    )

    # Costos
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Subtotal'
    )
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Impuestos'
    )
    shipping_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Costo de Envío'
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Descuento'
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Total'
    )

    # Fechas
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado')
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name='Confirmado')
    shipped_at = models.DateTimeField(null=True, blank=True, verbose_name='Enviado')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Completado')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizado')

    class Meta:
        db_table = 'orders_supplierorder'
        verbose_name = 'Orden del Proveedor'
        verbose_name_plural = 'Órdenes de Proveedores'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['provider', 'status']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        provider_name = self.provider.name if self.provider else f"Company {self.company_id}"
        return f"SupplierOrder #{self.id} - {provider_name}"

    @property
    def item_count(self):
        """Cantidad de items en esta SupplierOrder"""
        return self.items.aggregate(total=Sum('quantity'))['total'] or 0

    def calculate_totals(self):
        """Recalcula los totales basados en items"""
        self.subtotal = self.items.aggregate(
            total=Sum('total_price')
        )['total'] or Decimal('0.00')
        
        # Tax es parte del total_price ya
        self.total = self.subtotal + self.shipping_cost - self.discount_amount
        self.save()
