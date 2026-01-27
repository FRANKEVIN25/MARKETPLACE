
# orders/pricing/customer_discount.py


# esto se trabaja despues de trabajar los modelos de orders
"""
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum
from apps.orders.models import Order
from apps.discounts.models import DiscountRule
from dateutil.relativedelta import relativedelta
import math

ESTADOS_VALIDOS = ['pagado','validando','enviando','entregado']

def redondear_descuento_al_peso(monto_descuento):
    if monto_descuento <= Decimal('0'):
        return Decimal('0.00')
    
    # Convertir a float para usar math.round, luego volver a Decimal
    float_val = float(monto_descuento)
    redondeado = round(float_val)  # Redondeo matemático estándar
    
    return Decimal(str(redondeado)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def _suma_periodo(cliente, inicio, fin_excl):
    qs = Order.objects.filter(
        user=cliente,
        status__in=ESTADOS_VALIDOS,
        paid_at__gte=inicio,
        paid_at__lt=fin_excl,
    )
    return qs.aggregate(total=Sum('total'))['total'] or Decimal('0.00')

def gasto_ponderado(cliente, esquema_dias_y_peso):

    # Ej.: (0, 30, Decimal('0.70')) => hoy..30 días atrás con peso 0.70

    ahora = timezone.now()
    total = Decimal('0.00')
    for d_ini, d_fin, w in esquema_dias_y_peso:
        fin_excl = ahora - relativedelta(days=d_ini)
        inicio   = ahora - relativedelta(days=d_fin)
        periodo  = _suma_periodo(cliente, inicio, fin_excl)
        total   += (periodo * w)
    return total

def get_customer_type(customer):
    return customer.customer_type

def calcular_descuento_cliente(cliente, monto_carrito):

    #Devuelve (porcentaje_descuento: Decimal, monto_descuento: Decimal)
    #CON REDONDEO AL PESO desde el origen

    if not cliente or not getattr(cliente, 'is_authenticated', False):
        return Decimal('0'), Decimal('0')

    tipo = get_customer_type(cliente)

    if tipo == 'empresarial':
        # 70% (0-30 días) + 30% (31-90 días)
        esquema = [
            (0, 30,  Decimal('0.70')),
            (31, 90, Decimal('0.30')),
        ]
    else:
        # 'individual': 60% (0-90 días) + 40% (91-240 días)
        esquema = [
            (0, 90,    Decimal('0.60')),
            (91, 240,  Decimal('0.40')),
        ]

    historial_ponderado = gasto_ponderado(cliente, esquema)

    # Suma ponderada + ticket actual para buscar el tier
    monto_total = historial_ponderado + Decimal(str(monto_carrito))

    configuraciones = DiscountRule.objects.filter(
        tipo_cliente=tipo, monto_minimo__lte=monto_total, activo=True
    ).order_by('-monto_minimo')

    porcentaje = configuraciones.first().porcentaje_descuento if configuraciones.exists() else Decimal('0')
    
    # Calcular descuento exacto
    monto_desc_exacto = (Decimal(str(monto_carrito)) * Decimal(str(porcentaje))) / Decimal('100')
    
    # REDONDEAR AL PESO MÁS CERCANO desde aquí
    monto_desc_redondeado = redondear_descuento_al_peso(monto_desc_exacto)
    
    return porcentaje, monto_desc_redondeado


"""

"""
Historial ponderado = 0.60*700 + 0.40*1000 = 420 + 400 = 820
Monto para tier = 820 + 400 = 1220 → cae en la regla >= 1000 → 5%
Descuento = 400 * 0.05 = S/ 20.00
Porcentaje descuento = 5%
"""

"""
    Precio base (Product.price)
            ↓
    Descuento por cliente (historial / tipo)
            ↓
    Cupón (opcional)
            ↓
    Impuestos
            ↓
    Precio final mostrado
"""

