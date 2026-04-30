from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.customer.models import Customer
from apps.marketplace.models import Provider
from apps.orders.models import Order, OrderItem, SubOrder
from apps.products.models import Product


class OrderHistoryTests(APITestCase):
	def setUp(self):
		user_model = get_user_model()
		self.user = user_model.objects.create_user(
			username='orders-user',
			email='orders@example.com',
			password='testpass123'
		)
		self.client.force_authenticate(user=self.user)
		self.customer = Customer.objects.create(user=self.user)
		self.provider = Provider.objects.create(
			name='Proveedor Orders',
			owner=self.user,
			is_active=True,
			is_approved=True,
		)
		self.product = Product.objects.create(
			provider=self.provider,
			name='Pastillas de freno',
			reference='SKU-ORD-001',
			price=Decimal('120.00'),
			tax_percent=Decimal('18.00'),
			is_active=True,
			is_published=True,
			total_stock_cached=Product.MIN_STOCK_THRESHOLD + 5,
		)
		self.url = reverse('order-list')

	def test_order_history_lists_customer_orders_with_items(self):
		order = Order.objects.create(
			customer=self.customer,
			delivery_method='domicilio',
			subtotal=Decimal('120.00'),
			tax=Decimal('21.60'),
			total=Decimal('141.60'),
		)
		sub_order = SubOrder.objects.create(
			order=order,
			provider=self.provider,
			subtotal=Decimal('120.00'),
			igv_rate=Decimal('18.00'),
			igv_amount=Decimal('21.60'),
			total=Decimal('141.60'),
		)
		OrderItem.objects.create(
			sub_order=sub_order,
			product=self.product,
			provider=self.provider,
			product_name=self.product.name,
			product_sku=self.product.reference,
			quantity=1,
			unit_price=Decimal('120.00'),
			igv_rate=Decimal('18.00'),
			igv_amount=Decimal('21.60'),
		)

		response = self.client.get(self.url)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data['count'], 1)
		order_data = response.data['results'][0]
		self.assertEqual(order_data['order_number'], order.order_number)
		self.assertEqual(len(order_data['sub_orders']), 1)
		self.assertEqual(len(order_data['items']), 1)
		self.assertEqual(order_data['items'][0]['product_name'], self.product.name)
