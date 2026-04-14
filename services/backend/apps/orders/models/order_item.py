# orders/models/order_item.py
"""
OrderItem - Snapshot de producto en el momento de la compra.
"""

from django.db import models

from .sub_order import SubOrder


class OrderItem(models.Model):
    """
    Item individual de una orden (producto)
    """
    # Relaciones
    sub_order = models.ForeignKey(
        SubOrder,
        on_delete=models.CASCADE,
        related_name='items'
    )
    
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        related_name='order_items'
    )
    
    provider = models.ForeignKey(
        'marketplace.Provider',
        on_delete=models.PROTECT,
        related_name='order_items',
        help_text="Denormalizado para queries rápidas"
    )
    
    # Snapshot de datos del producto
    product_name = models.CharField(
        max_length=200,
        help_text="Snapshot del nombre"
    )
    
    product_sku = models.CharField(
        max_length=100,
        blank=True,
        help_text="Snapshot del SKU"
    )
    
    # Cantidad y precio
    quantity = models.PositiveIntegerField(default=1)
    
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Precio unitario (snapshot)"
    )
    
    # IGV (snapshot)
    igv_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Tasa de IGV aplicada (snapshot)"
    )
    
    igv_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Monto de IGV para este item"
    )
    
    # Descuento
    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    # Subtotal
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="(unit_price * quantity) - discount + igv_amount"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'orders_orderitem'
        verbose_name = 'Item de Orden'
        verbose_name_plural = 'Items de Orden'
        ordering = ['id']
        indexes = [
            models.Index(fields=['sub_order', 'product']),
            models.Index(fields=['provider']),
        ]
    
    def __str__(self):
        return f"{self.product_name} x{self.quantity}"
    
    def save(self, *args, **kwargs):
        # Calcular subtotal automáticamente
        base = self.unit_price * self.quantity
        base_con_descuento = base - self.discount
        self.subtotal = base_con_descuento + self.igv_amount
        super().save(*args, **kwargs)

