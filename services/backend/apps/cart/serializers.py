
from rest_framework import serializers
from .models import Cart, CartLine
from cart.services.cart_calculator import CartCalculator
from products.serializers import ProductListSerializer

class CartLineSerializer(serializers.ModelSerializer):
	product = ProductListSerializer(read_only=True)
	provider_name = serializers.CharField(source='provider.name', read_only=True)

	class Meta:
		model = CartLine
		fields = [
			'id', 'cart', 'product', 'provider', 'provider_name',
			'product_name', 'product_reference', 'price_unit', 'tax_percent',
			'quantity', 'is_available', 'stock_checked_at', 'added_at'
		]
		read_only_fields = [
			'id', 'cart', 'product', 'provider', 'provider_name',
			'product_name', 'product_reference', 'price_unit', 'tax_percent',
			'is_available', 'stock_checked_at', 'added_at'
		]

class CartSerializer(serializers.ModelSerializer):
	lines = CartLineSerializer(many=True, read_only=True)
	totals = serializers.SerializerMethodField()

	class Meta:
		model = Cart
		fields = [
			'id', 'user', 'session_key', 'status', 'currency',
			'lines', 'totals', 'created_at', 'updated_at'
		]
		read_only_fields = [
			'id', 'user', 'session_key', 'status', 'currency',
			'lines', 'totals', 'created_at', 'updated_at'
		]

	def get_totals(self, obj):
		summaries = CartCalculator.calculate(obj)
		# Convertir a dict serializable
		return {
			str(provider): {
				'subtotal': float(data['subtotal']),
				'tax': float(data['tax'])
			}
			for provider, data in summaries.items()
		}
# Serializers para el carrito de compras
