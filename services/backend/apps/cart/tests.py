from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.cart.models import CartLine
from apps.marketplace.models import Provider
from apps.products.models import Product


class CartAddLineTests(APITestCase):
	def setUp(self):
		user_model = get_user_model()
		self.user = user_model.objects.create_user(
			username='cart-user',
			email='cart@example.com',
			password='testpass123'
		)
		self.client.force_authenticate(user=self.user)
		self.provider = Provider.objects.create(
			name='Proveedor Test',
			owner=self.user,
			is_active=True,
			is_approved=True,
		)
		self.url = reverse('cart-add-line')

	def create_product(self, **overrides):
		data = {
			'provider': self.provider,
			'name': 'Filtro de aire',
			'reference': 'SKU-001',
			'price': Decimal('47.20'),
			'tax_percent': Decimal('18.00'),
			'is_active': True,
			'is_published': True,
			'total_stock_cached': Product.MIN_STOCK_THRESHOLD + 3,
		}
		data.update(overrides)
		return Product.objects.create(**data)

	def test_add_line_allows_published_available_product(self):
		product = self.create_product()

		response = self.client.post(
			self.url,
			{'product_id': product.id, 'quantity': 1},
			format='json'
		)

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(CartLine.objects.count(), 1)
		line = CartLine.objects.get()
		self.assertEqual(line.product_id, product.id)
		self.assertTrue(line.is_available)

	def test_add_line_rejects_unpublished_product(self):
		product = self.create_product(reference='SKU-002', is_published=False)

		response = self.client.post(
			self.url,
			{'product_id': product.id, 'quantity': 1},
			format='json'
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(response.data['error'], 'El producto no está disponible.')
		self.assertFalse(CartLine.objects.exists())
