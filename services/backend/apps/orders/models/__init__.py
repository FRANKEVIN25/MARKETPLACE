from .order import Order
from .supplier_order import SupplierOrder
from .order_item import OrderItem

# Aliases para compatibilidad con views/serializers existentes
SubOrder = SupplierOrder

__all__ = ['Order', 'SupplierOrder', 'SubOrder', 'OrderItem']

# PaymentProof aún no implementado - placeholder
from django.db import models
class PaymentProof(models.Model):
    class Meta:
        app_label = 'orders'
        managed = False  # No crea tabla
    PAYMENT_METHOD_CHOICES = []
