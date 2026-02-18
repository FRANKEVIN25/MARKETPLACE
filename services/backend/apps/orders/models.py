"""
Modelos de Órdenes - Modelo Descentralizado
"""
from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from shortuuid.django_fields import ShortUUIDField


class Order(models.Model):
    """
    Orden principal del cliente (puede contener productos de múltiples proveedores)
    """
    STATUS_CHOICES = [
        ('pendiente_pago', 'Pendiente de Pago'),
        ('pagado', 'Pagado'),
        ('procesando', 'Procesando'),
        ('enviado', 'Enviado'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
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
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_order_number():
        """Genera número de orden: ORD-2026-00001"""
        from django.utils import timezone
        year = timezone.now().year
        
        # Obtener el último número del año
        last_order = Order.objects.filter(
            order_number__startswith=f'ORD-{year}-'
        ).order_by('-order_number').first()
        
        if last_order:
            last_num = int(last_order.order_number.split('-')[-1])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f'ORD-{year}-{new_num:05d}'
    
    @property
    def provider_count(self):
        """Cantidad de proveedores en esta orden"""
        return self.sub_orders.count()


class SubOrder(models.Model):
    """
    Sub-orden por proveedor (División de la orden principal)
    """
    STATUS_CHOICES = [
        ('pendiente_pago', 'Pendiente de Pago'),
        ('pago_pendiente_confirmacion', 'Pago Pendiente de Confirmación'),
        ('pagado_confirmado', 'Pago Confirmado'),
        ('pago_rechazado', 'Pago Rechazado'),
        ('procesando', 'Procesando'),
        ('enviado', 'Enviado'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
    ]
    
    # Relaciones
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='sub_orders'
    )
    
    provider = models.ForeignKey(
        'marketplace.Provider',
        on_delete=models.PROTECT,
        related_name='sub_orders'
    )
    
    # Identificación
    sub_order_number = models.CharField(
        max_length=60,
        unique=True,
        db_index=True,
        help_text="ORD-2026-00001-A"
    )
    
    # Estado
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='pendiente_pago',
        db_index=True
    )
    
    # Montos (snapshot)
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    igv_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=18.00,
        help_text="Tasa de IGV (18.00 o 0.00)"
    )
    
    igv_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Monto IGV"
    )
    
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    # Integración con Odoo
    odoo_sale_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="ID de la Sale Order en Odoo"
    )
    
    odoo_invoice_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="ID de la factura en Odoo"
    )
    
    # Rechazo de pago
    rejection_reason = models.TextField(
        blank=True,
        verbose_name="Motivo de Rechazo"
    )
    
    # Tracking
    tracking_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Número de Seguimiento"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Confirmación de Pago"
    )
    
    class Meta:
        db_table = 'orders_suborder'
        verbose_name = 'Sub-Orden'
        verbose_name_plural = 'Sub-Órdenes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'provider']),
            models.Index(fields=['provider', 'status']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.sub_order_number} - {self.provider.name}"
    
    def save(self, *args, **kwargs):
        if not self.sub_order_number:
            self.sub_order_number = self.generate_sub_order_number()
        super().save(*args, **kwargs)
    
    def generate_sub_order_number(self):
        """Genera: ORD-2026-00001-A, ORD-2026-00001-B, etc."""
        import string
        existing_count = SubOrder.objects.filter(order=self.order).count()
        letter = string.ascii_uppercase[existing_count]
        return f"{self.order.order_number}-{letter}"


class OrderItem(models.Model):
    """
    Item individual de una orden (producto)
    """
    # Relaciones
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    
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
            models.Index(fields=['order', 'product']),
            models.Index(fields=['sub_order']),
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


class PaymentProof(models.Model):
    """
    Comprobante de pago subido por el cliente
    """
    PAYMENT_METHOD_CHOICES = [
        ('transferencia', 'Transferencia Bancaria'),
        ('yape', 'Yape'),
        ('plin', 'Plin'),
        ('efectivo_contraentrega', 'Efectivo Contraentrega'),
        ('efectivo_tienda', 'Efectivo en Tienda'),
    ]
    
    # Relación
    sub_order = models.ForeignKey(
        SubOrder,
        on_delete=models.CASCADE,
        related_name='payment_proofs'
    )
    
    # Método de pago
    payment_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHOD_CHOICES
    )
    
    # Comprobante
    file = models.ImageField(
        upload_to='payment_proofs/%Y/%m/',
        help_text="Voucher/Captura de pantalla"
    )
    
    operation_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Número de Operación"
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Monto pagado según voucher"
    )
    
    # Validación
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='uploaded_payment_proofs'
    )
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_payment_proofs',
        help_text="Proveedor que verificó el pago"
    )
    
    verified_at = models.DateTimeField(
        null=True,
        blank=True
    )
    
    verification_notes = models.TextField(
        blank=True,
        verbose_name="Notas de Verificación"
    )
    
    class Meta:
        db_table = 'orders_paymentproof'
        verbose_name = 'Comprobante de Pago'
        verbose_name_plural = 'Comprobantes de Pago'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['sub_order', 'uploaded_at']),
        ]
    
    def __str__(self):
        return f"Pago {self.get_payment_method_display()} - {self.sub_order.sub_order_number}"
