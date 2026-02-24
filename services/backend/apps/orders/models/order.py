

"""
apps/orders/models/order.py

Una Order puede tener múltiples proveedores (Provider/Marketplace).
Cada SupplierOrder agrupa items del mismo proveedor.
El stock real se consulta desde StockItem.

Arquitectura:
    Order (cliente)
    ├── SupplierOrder (Provider A - Distribuidor)
    │   ├── OrderItem (Producto A del Distribuidor)
    │   ├── OrderItem (Producto B del Distribuidor)
    │
    ├── SupplierOrder (Provider B - Oficial)
    │   ├── OrderItem (Producto C del Oficial)
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from django.core.exceptions import ValidationError

User = get_user_model()


class Order(models.Model):
    """
    Orden de Compra - Agregador de múltiples proveedores.
    
    El cliente crea UNA orden que puede contener productos de MÚLTIPLES proveedores.
    Cada proveedor tendrá su SupplierOrder asociada.
    """

    STATUS_CHOICES = [
        ('borrador', 'Borrador'),
        ('pago_pendiente', 'Pago pendiente'),
        ('pagado', 'Pagado'),
        ('procesando', 'Procesando'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    ]

    # Identificación única
    order_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Número de Orden',
        help_text='Identificador único de la orden'
    )

    # Relaciones
    customer = models.ForeignKey(
        "customer.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Cliente'
    )

    # Estado
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='borrador',
        verbose_name='Estado',
        db_index=True
    )

    # Fechas
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado')
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name='Pagado el')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizado')

    # Totales (calculados, no autoritativos)
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Subtotal'
    )
    discount_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Descuentos'
    )
    shipping_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Envío'
    )
    tax_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Impuestos'
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Total'
    )

    currency = models.CharField(
        max_length=10,
        default='PEN',
        verbose_name='Moneda'
    )

    # Dirección de entrega
    shipping_address = models.ForeignKey(
        'customer.Address',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders_shipped_to',
        verbose_name='Dirección de Envío'
    )

    # Notas
    notes = models.TextField(blank=True, verbose_name='Notas')

    class Meta:
        db_table = 'orders_order'
        verbose_name = 'Orden'
        verbose_name_plural = 'Órdenes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['order_number']),
        ]

    def __str__(self):
        return f"Order {self.order_number} ({self.status})"

    @property
    def supplier_count(self):
        """Cantidad de proveedores en esta orden"""
        return self.supplier_orders.count()

    @property
    def item_count(self):
        """Total de items en la orden"""
        from django.db.models import Sum
        count = self.supplier_orders.aggregate(
            total=Sum('items__quantity')
        )['total'] or 0
        return count

    def can_be_paid(self):
        """Validar si la orden puede pagarse"""
        return self.status == 'pago_pendiente' and self.total > 0
