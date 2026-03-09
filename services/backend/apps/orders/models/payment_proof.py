


"""
apps/orders/models/payment_proof.py

PaymentProof actúa como PaymentTransaction implícita:
cada registro es un intento de pago por una SubOrder.
Una SubOrder puede tener múltiples PaymentProofs (reintentos tras rechazo).
Solo uno puede estar en status='approved' a la vez.

Acceso desde SubOrder:
    sub_order.payments.all()
    sub_order.payments.filter(status='approved').first()
    sub_order.payments.order_by('-uploaded_at').first()
"""

from django.db import models
from django.conf import settings

from .sub_order import SubOrder


class PaymentProof(models.Model):
    """
    Comprobante / intento de pago asociado a una SubOrder.
    Permite múltiples intentos, historial completo y auditoría.
    """

    STATUS_CHOICES = [
        ('uploaded', 'Comprobante Subido'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('transferencia',          'Transferencia Bancaria'),
        ('yape',                   'Yape'),
        ('plin',                   'Plin'),
        ('efectivo_contraentrega', 'Efectivo Contraentrega'),
        ('efectivo_tienda',        'Efectivo en Tienda'),
    ]

    # Relación — related_name='payments' (uso semántico: sub_order.payments.all())
    sub_order = models.ForeignKey(
        SubOrder,
        on_delete=models.CASCADE,
        related_name='payments'
    )

    # Datos del pago
    payment_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHOD_CHOICES
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    operation_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Número de Operación"
    )

    # Imagen del comprobante (opcional para pagos futuros vía API/pasarela)
    file = models.ImageField(
        upload_to='payment_proofs/%Y/%m/',
        blank=True,
        help_text="Voucher/Captura de pantalla"
    )

    # ID externo para integraciones futuras (Culqi, Niubiz, MercadoPago, etc.)
    external_transaction_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="ID de transacción en pasarela de pago externa (uso futuro)"
    )

    # Estado del intento de pago
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='uploaded',
        db_index=True
    )

    # Motivo de rechazo (proveedor lo completa cuando status='rejected')
    rejection_reason = models.TextField(blank=True)

    # Auditoría
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='uploaded_payment_proofs'
    )

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_payment_proofs',
        help_text="Usuario (proveedor/admin) que revisó el comprobante"
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    verified_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'orders_paymentproof'
        verbose_name = 'Comprobante de Pago'
        verbose_name_plural = 'Comprobantes de Pago'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['sub_order', 'status']),
            models.Index(fields=['sub_order', 'uploaded_at']),
        ]

    def __str__(self):
        return (
            f"PaymentProof #{self.pk} — "
            f"{self.sub_order.sub_order_number} "
            f"[{self.get_status_display()}]"
        )

    @property
    def is_approved(self):
        return self.status == 'approved'

    @property
    def is_rejected(self):
        return self.status == 'rejected'
