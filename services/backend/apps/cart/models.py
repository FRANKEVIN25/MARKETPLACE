
from django.db import models
from django.conf import settings
from django.db.models import Q
from decimal import Decimal

class Cart(models.Model):
	"""
	Carrito lógico (puede vivir días).
	No calcula totales críticos: solo agrupa.
	"""
	STATUS_CHOICES = [
		('active', 'Activo'),
		('locked', 'Bloqueado (checkout)'),
		('abandoned', 'Abandonado'),
		('converted', 'Convertido en orden'),
	]

	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		null=True,
		blank=True,
		related_name='carts'
	)
	session_key = models.CharField(max_length=64, null=True, blank=True, db_index=True)

	status = models.CharField(
		max_length=20,
		choices=STATUS_CHOICES,
		default='active'
	)

	currency = models.CharField(max_length=10, default='PEN')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = 'cart_cart'
		indexes = [
			models.Index(fields=['user', 'status']),
			models.Index(fields=['session_key']),
		]
		constraints = [
			models.UniqueConstraint(
				fields=['user'],
				condition=Q(status='active') & Q(user__isnull=False),
				name='unique_active_cart_per_user',
			),
		]

	def __str__(self):
		return f"Cart #{self.id} ({self.status})"

class CartLine(models.Model):
	"""
	Línea de carrito (snapshot del producto).
	"""
	cart = models.ForeignKey(
		Cart,
		on_delete=models.CASCADE,
		related_name='lines'
	)

	# Snapshot del producto
	product = models.ForeignKey(
		'products.Product',
		on_delete=models.PROTECT
	)
	provider = models.ForeignKey(
		'marketplace.Provider',
		on_delete=models.PROTECT
	)

	# Datos congelados
	product_name = models.CharField(max_length=255)
	product_reference = models.CharField(max_length=50, null=True, blank=True)
	price_unit = models.DecimalField(max_digits=12, decimal_places=2)
	tax_percent = models.DecimalField(max_digits=5, decimal_places=2)

	quantity = models.PositiveIntegerField()

	# Flags de validación
	is_available = models.BooleanField(default=True)
	stock_checked_at = models.DateTimeField(null=True, blank=True)

	added_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = 'cart_cartline'
		unique_together = [('cart', 'product')]
		indexes = [
			models.Index(fields=['cart']),
			models.Index(fields=['provider']),
		]

	def __str__(self):
		return f"{self.product_name} x {self.quantity}"
