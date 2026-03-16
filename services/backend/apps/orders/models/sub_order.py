# orders/models/supplier_order.py
"""
SupplierOrder - Porción de una Order para un Proveedor específico.
"""

from django.db import models
from decimal import Decimal
from django.db.models import Sum
from .order import Order

class SubOrder(models.Model):
    """
    Sub-orden por proveedor (División de la orden principal)
    """
    STATUS_CHOICES = [
        # Máquina de estados lineal: 7 estados operativos (v5)
        # Las condiciones excepcionales (expiración, reembolso)
        # se representan como flags booleanos, NO como estados extra.
        #
        # Flujo normal:
        #   pendiente_pago → pago_en_revision → confirmado → enviado → entregado
        #
        # Flujo con rechazo:
        #   pago_en_revision → pago_rechazado → pago_en_revision → confirmado ...
        #
        # cancelado (desde cualquier etapa hasta 'confirmado')
        ('pendiente_pago',   'Pendiente de Pago'),  # solo Django/Svelte; timer activo
        ('pago_en_revision', 'Pago en Revisión'),   # comprobante subido; sale.order draft en Odoo
        ('pago_rechazado',   'Pago Rechazado'),     # proveedor rechazó el comprobante en Odoo
        ('confirmado',       'Confirmado'),         # proveedor confirmó cotización en Odoo (pago aprobado)
        ('enviado',          'Enviado'),            # luego de marcar Stock.picking como "hecho" o "done"
        ('entregado',        'Recibido'),           # cliente marca en historial-compra/[id] que ha recibido
        ('cancelado',        'Cancelado'),          # manual o por expiración del TTL
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
    
    # Motivo de rechazo del último comprobante (historial breve; el detalle estará en PaymentTransaction)
    rejection_reason = models.TextField(
        blank=True,
        verbose_name="Motivo de Rechazo"
    )

    # FLAGS DE AUDITORÍA (reemplazan a los estados 'pago_rechazado', 'expirada', 'reembolsada')
    payment_rejected = models.BooleanField(
        default=False,
        help_text="True si el último comprobante fue rechazado por el proveedor (status=pago_rechazado)."
    )
    expired = models.BooleanField(
        default=False,
        help_text="True si status=cancelado fue causado por vencimiento del TTL (3h sin pago)."
    )
    refunded = models.BooleanField(
        default=False,
        help_text="True si se procesó un reembolso para esta SubOrder."
    )

    # TRAZABILIDAD ODOO
    odoo_sync_error = models.BooleanField(
        default=False,
        help_text="True si Celery agotó reintentos al sincronizar con Odoo."
    )
    odoo_sync_error_detail = models.TextField(
        blank=True,
        help_text="Detalle del último error de sincronización con Odoo."
    )

    # TRAZABILIDAD OPERATIVA
    shipped_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Despacho"
    )
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Entrega"
    )
    refund_notes = models.TextField(
        blank=True,
        help_text="Notas del reembolso procesado."
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

