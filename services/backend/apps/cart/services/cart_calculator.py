# cart/services/cart_calculator.py
from decimal import Decimal
# Servicio auxiliar para calcular totales
class CartCalculator:
	@staticmethod
	def calculate(cart):
		summaries = {}
		for line in cart.lines.all():
			subtotal = line.price_unit * line.quantity
			tax = subtotal * (line.tax_percent / Decimal('100'))
			prov = line.provider
			if prov not in summaries:
				summaries[prov] = {
					'subtotal': Decimal('0'),
					'tax': Decimal('0'),
				}
			summaries[prov]['subtotal'] += subtotal
			summaries[prov]['tax'] += tax
		return summaries