
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import Cart, CartLine
from .serializers import CartSerializer, CartLineSerializer
from apps.products.models import Product
from django.shortcuts import get_object_or_404

class CartViewSet(viewsets.ViewSet):
	"""
	API para gestionar el carrito de compras (modelo robusto)
	"""
	permission_classes = [IsAuthenticated]
	def get_cart(self, request):
		user = request.user if request.user.is_authenticated else None
		session_key = request.session.session_key or request.session.create()

		if user:
			cart = Cart.objects.filter(user=user, status='active').first()
		else:
			cart = Cart.objects.filter(session_key=session_key, status='active').first()

		if not cart:
			cart = Cart.objects.create(
				user=user,
				session_key=session_key,
				status='active',
			)
		return cart

	def list(self, request):
		cart = self.get_cart(request)
		cart = Cart.objects.prefetch_related(
			'lines__provider',
			'lines__product',
		).get(pk=cart.pk)
		serializer = CartSerializer(cart)
		return Response(serializer.data)

	@action(detail=False, methods=['post'])
	def add_line(self, request):
		cart = self.get_cart(request)
		product_id = request.data.get('product_id')
		quantity = request.data.get('quantity', 1)
		try:
			quantity = int(quantity)
		except (TypeError, ValueError):
			return Response({'error': 'Cantidad inválida.'}, status=status.HTTP_400_BAD_REQUEST)
		if quantity < 1:
			return Response({'error': 'La cantidad debe ser al menos 1.'}, status=status.HTTP_400_BAD_REQUEST)

		product = get_object_or_404(Product, id=product_id)

		if not product.is_available:
			return Response({'error': 'El producto no está disponible.'}, status=status.HTTP_400_BAD_REQUEST)

		available_stock = product.total_stock_cached
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
				'quantity': min(quantity, available_stock),
				'is_available': True,
				'stock_checked_at': timezone.now(),
			}
		)
		if not created:
			new_qty = min(line.quantity + quantity, available_stock)
			line.quantity = new_qty
			line.is_available = True
			line.stock_checked_at = timezone.now()
			line.save(update_fields=['quantity', 'is_available', 'stock_checked_at'])
		serializer = CartLineSerializer(line)
		return Response(serializer.data, status=status.HTTP_201_CREATED)

	@action(detail=False, methods=['post'])
	def update_quantity(self, request):
		cart = self.get_cart(request)
		product_id = request.data.get('product_id')
		quantity = request.data.get('quantity')
		try:
			quantity = int(quantity)
		except (TypeError, ValueError):
			return Response({'error': 'Cantidad inválida.'}, status=status.HTTP_400_BAD_REQUEST)
		if quantity < 1:
			return Response({'error': 'La cantidad debe ser al menos 1.'}, status=status.HTTP_400_BAD_REQUEST)
		line = get_object_or_404(CartLine, cart=cart, product_id=product_id)
		available_stock = line.product.total_stock_cached
		line.quantity = min(quantity, available_stock)
		line.save(update_fields=['quantity'])
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
