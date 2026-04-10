

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


User = get_user_model()

class Order(models.Model):
    """
    Orden principal del cliente (puede contener productos de múltiples proveedores)
    """
    STATUS_CHOICES = [
        # Order.status NUNCA se escribe manualmente.
        # Siempre se deriva de los estados de sus SubOrders (ver signals.py → recalculate_order_status)
        ('pendiente_pago', 'Pendiente de Pago'),   # al menos una SubOrder sin pagar
        ('pagado',         'Pagado'),               # todas las SubOrders activas pagadas en svelte
        ('procesando',     'Procesando'),           # al menos una SubOrder confirmada en Odoo
        ('enviado',        'Enviado'),              # al menos una SubOrder despachada
        ('completado',     'Completado'),           # todas las SubOrders activas entregadas
        ('cancelado',      'Cancelado'),            # todas las SubOrders canceladas
    ]
    
    DELIVERY_METHOD_CHOICES = [
        ('domicilio', 'Envío a Domicilio'),
        ('agencia', 'Envío a Agencia'),
        ('tienda', 'Recojo en Tienda'),
    ]
    
    # Identificación
    order_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="ORD-2026-00001"
    )
    
    # Cliente
    customer = models.ForeignKey(
        'customer.Customer',
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name="Cliente"
    )
    
    # Estado
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pendiente_pago',
        db_index=True
    )
    
    # Método de entrega
    delivery_method = models.CharField(
        max_length=20,
        choices=DELIVERY_METHOD_CHOICES,
        default='domicilio'
    )
    
    # Dirección de envío
    shipping_address = models.ForeignKey(
        'customer.Address',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='orders',
        help_text="Dirección de envío (null si es recojo en tienda)"
    )
    
    # Montos
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Subtotal"
    )
    
    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Descuento"
    )
    
    tax = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Impuestos (IGV)"
    )
    
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Total"
    )
    
    # Notas
    customer_notes = models.TextField(
        blank=True,
        verbose_name="Notas del Cliente"
    )
    
    # Deadline de pago (TTL 3 horas desde la creación)
    # Pasado este plazo, las SubOrders en 'pendiente_pago' expiran automáticamente
    # via la tarea Celery expire_pending_suborders
    payment_deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Plazo máximo de pago (created_at + 3h). Las SubOrders pendientes expiran al vencer."
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'orders_order'
        verbose_name = 'Orden'
        verbose_name_plural = 'Órdenes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['order_number']),
        ]
    
    def __str__(self):
        return f"{self.order_number} - {self.customer}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            from django.db import transaction
            from django.utils import timezone
            year = timezone.now().year
            prefix = f'ORD-{year}-'
            with transaction.atomic():
                # select_for_update() serializa creaciones concurrentes:
                # el row lock se mantiene hasta que la transacción externa
                # (ej. @transaction.atomic en create_order) haga commit.
                last_order = (
                    Order.objects
                    .select_for_update()
                    .filter(order_number__startswith=prefix)
                    .order_by('-order_number')
                    .first()
                )
                new_num = (int(last_order.order_number.split('-')[-1]) + 1) if last_order else 1
                self.order_number = f'{prefix}{new_num:05d}'
                super().save(*args, **kwargs)
            return
        super().save(*args, **kwargs)
    
    @property
    def provider_count(self):
        """Cantidad de proveedores en esta orden"""
        return self.sub_orders.count()

