
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Cart, CartLine
from .serializers import CartSerializer, CartLineSerializer
from products.models import Product
from marketplace.models import Provider
from django.shortcuts import get_object_or_404

class CartViewSet(viewsets.ViewSet):
	"""
	API para gestionar el carrito de compras (modelo robusto)
	"""
	def get_cart(self, request):
		user = request.user if request.user.is_authenticated else None
		session_key = request.session.session_key or request.session.create()
		cart, _ = Cart.objects.get_or_create(user=user, session_key=session_key)
		return cart

	def list(self, request):
		cart = self.get_cart(request)
		serializer = CartSerializer(cart)
		return Response(serializer.data)

	@action(detail=False, methods=['post'])
	def add_line(self, request):
		cart = self.get_cart(request)
		product_id = request.data.get('product_id')
		quantity = int(request.data.get('quantity', 1))
		product = get_object_or_404(Product, id=product_id)
		provider = product.provider
		# Snapshot
		line, created = CartLine.objects.get_or_create(
			cart=cart,
			product=product,
			defaults={
				'provider': provider,
				'product_name': product.name,
				'product_reference': product.reference,
				'price_unit': product.price,
				'tax_percent': product.tax_percent,
				'quantity': quantity,
			}
		)
		if not created:
			line.quantity += quantity
			line.save()
		serializer = CartLineSerializer(line)
		return Response(serializer.data, status=status.HTTP_201_CREATED)

	@action(detail=False, methods=['post'])
	def update_quantity(self, request):
		cart = self.get_cart(request)
		product_id = request.data.get('product_id')
		quantity = int(request.data.get('quantity', 1))
		line = get_object_or_404(CartLine, cart=cart, product_id=product_id)
		line.quantity = quantity
		line.save()
		serializer = CartLineSerializer(line)
		return Response(serializer.data)

	@action(detail=False, methods=['post'])
	def remove_line(self, request):
		cart = self.get_cart(request)
		product_id = request.data.get('product_id')
		line = get_object_or_404(CartLine, cart=cart, product_id=product_id)
		line.delete()
		return Response({'removed': True})

	@action(detail=False, methods=['post'])
	def clear(self, request):
		cart = self.get_cart(request)
		cart.lines.all().delete()
		return Response({'cleared': True})
from django.shortcuts import render

# Create your views here.
