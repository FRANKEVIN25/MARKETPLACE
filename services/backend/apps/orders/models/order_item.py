# orders/models/order_item.py
"""
OrderItem - Snapshot de producto en el momento de la compra.
"""

from django.db import models
from decimal import Decimal


class OrderItem(models.Model):
    """
    Representa UNA línea de producto en UNA SupplierOrder.
    
    Es un snapshot (foto) del estado del producto en el momento de compra:
    - Precio
    - Nombre
    - Cantidad
    
    No se modifica después de la creación (auditoría).
    """

    # Relación con SupplierOrder
    supplier_order = models.ForeignKey(
        'orders.SupplierOrder',
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Orden del Proveedor'
    )

    # Referencias del producto (snapshot)
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items',
        verbose_name='Producto'
    )

    # Datos capturados en el momento de la compra
    product_id_snapshot = models.IntegerField(
        help_text="ID del producto en Odoo (capturado al momento de compra)"
    )
    
    sku = models.CharField(
        max_length=100,
        verbose_name='SKU',
        help_text='SKU del producto en el momento de compra'
    )
    
    name = models.CharField(
        max_length=255,
        verbose_name='Nombre de Producto',
        help_text='Nombre del producto en el momento de compra'
    )

    # Cantidad y precios
    quantity = models.PositiveIntegerField(verbose_name='Cantidad')
    
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Precio Unitario',
        help_text='Precio sin impuesto'
    )
    
    tax_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('18.00'),
        verbose_name='% Impuesto'
    )
    
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Monto Impuesto'
    )
    
    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Precio Total',
        help_text='unit_price * quantity (sin impuesto)'
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizado')

    class Meta:
        db_table = 'orders_orderitem'
        verbose_name = 'Item de Orden'
        verbose_name_plural = 'Items de Órdenes'
        ordering = ['supplier_order', 'id']
        indexes = [
            models.Index(fields=['supplier_order']),
            models.Index(fields=['product']),
        ]

    def __str__(self):
        return f"{self.quantity}x {self.name} - ${self.unit_price}"

    def save(self, *args, **kwargs):
        """Calcular automaticamente tax_amount y total_price"""
        # Calcular impuesto
        self.tax_amount = self.unit_price * self.quantity * (self.tax_percent / 100)
        # Total es quantity * unit_price (impuesto va aparte)
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)
