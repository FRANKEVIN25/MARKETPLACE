# orders/pricing/customer_discount.py
"""
Motor de descuentos por historial cliente-proveedor.

Regla de negocio:
  El descuento se calcula por SubOrder, usando el historial de compras
  del cliente con ese proveedor específico (no el historial global).

Ponderación del historial:
  - company:    70% de los últimos 30 días + 30% de los últimos 31-90 días
  - individual: 60% de los últimos 0-90 días + 40% de los últimos 91-240 días

Prioridad de reglas en DiscountRule:
  1. Regla del proveedor específico (provider=<provider>)
  2. Regla global (provider=null) — fallback
  En ambos casos se elige la regla con mayor min_amount que no supere el
  historial ponderado + monto actual de la sub-orden.
"""

from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum, Q
from dateutil.relativedelta import relativedelta

# Lazy imports para evitar ciclos en arranque de Django
def _get_models():
    from apps.orders.models import SubOrder
    from apps.discounts.models import DiscountRule
    return SubOrder, DiscountRule


ESTADOS_VALIDOS = ['confirmado', 'enviado', 'entregado']


def _redondear_al_sol(monto: Decimal) -> Decimal:
    """Redondea el monto de descuento al sol más cercano (sin centavos)."""
    if monto <= Decimal('0'):
        return Decimal('0.00')
    redondeado = round(float(monto))
    return Decimal(str(redondeado)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _suma_periodo(customer, provider, inicio, fin_excl) -> Decimal:
    """Suma el total de SubOrders válidas del cliente con ese proveedor en el período dado."""
    SubOrder, _ = _get_models()
    qs = SubOrder.objects.filter(
        order__customer=customer,
        provider=provider,
        status__in=ESTADOS_VALIDOS,
        confirmed_at__gte=inicio,
        confirmed_at__lt=fin_excl,
    )
    return qs.aggregate(total=Sum('total'))['total'] or Decimal('0.00')


def _historial_ponderado(customer, provider, esquema) -> Decimal:
    """
    Calcula el historial de compra ponderado del cliente con el proveedor.
    `esquema` es una lista de tuplas (dias_ini, dias_fin, peso).
    """
    ahora = timezone.now()
    total = Decimal('0.00')
    for d_ini, d_fin, peso in esquema:
        fin_excl = ahora - relativedelta(days=d_ini)
        inicio   = ahora - relativedelta(days=d_fin)
        periodo  = _suma_periodo(customer, provider, inicio, fin_excl)
        total   += periodo * peso
    return total


def _esquema_ponderacion(customer_type: str):
    if customer_type == 'company':
        return [
            (0,  30, Decimal('0.70')),
            (31, 90, Decimal('0.30')),
        ]
    # individual (default)
    return [
        (0,  90,  Decimal('0.60')),
        (91, 240, Decimal('0.40')),
    ]


def _buscar_regla(customer_type: str, provider, monto_total: Decimal):
    """
    Busca la regla de descuento más favorable, priorizando regla por proveedor
    sobre regla global. Devuelve el Decimal del porcentaje o Decimal('0').
    """
    _, DiscountRule = _get_models()

    # 1. Regla específica del proveedor
    regla = (
        DiscountRule.objects
        .filter(
            customer_type=customer_type,
            provider=provider,
            min_amount__lte=monto_total,
            is_active=True,
        )
        .order_by('-min_amount')
        .first()
    )
    if regla:
        return regla.discount_percent

    # 2. Fallback: regla global (provider=null)
    regla_global = (
        DiscountRule.objects
        .filter(
            customer_type=customer_type,
            provider__isnull=True,
            min_amount__lte=monto_total,
            is_active=True,
        )
        .order_by('-min_amount')
        .first()
    )
    return regla_global.discount_percent if regla_global else Decimal('0')


def calcular_descuento_suborder(customer, provider, subtotal_suborder: Decimal):
    """
    Calcula el descuento para una SubOrder dados el cliente, el proveedor y
    el subtotal (sin IGV) de esa sub-orden.

    Devuelve:
        porcentaje (Decimal): porcentaje de descuento aplicado (ej. 5.00)
        monto      (Decimal): monto en soles redondeado al sol más cercano
    """
    if not customer:
        return Decimal('0'), Decimal('0.00')

    customer_type = customer.customer_type
    esquema = _esquema_ponderacion(customer_type)
    historial = _historial_ponderado(customer, provider, esquema)

    # Tier se busca con historial + ticket actual
    monto_total = historial + Decimal(str(subtotal_suborder))

    porcentaje = _buscar_regla(customer_type, provider, monto_total)

    if porcentaje <= Decimal('0'):
        return Decimal('0'), Decimal('0.00')

    monto_exacto = (Decimal(str(subtotal_suborder)) * porcentaje) / Decimal('100')
    monto_redondeado = _redondear_al_sol(monto_exacto)

    return porcentaje, monto_redondeado


