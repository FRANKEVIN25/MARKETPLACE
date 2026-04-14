from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.customer.models import Customer
from apps.marketplace.models import Provider, ProviderReview, ProviderReviewStatusChoices
from apps.orders.models import Order, SubOrder


class Command(BaseCommand):
    help = 'Carga reseñas de prueba para proveedores a partir de customers existentes.'

    REVIEW_BLUEPRINTS = [
        {
            'customer_username': 'cliente_jperez',
            'provider_name': 'AutoPartes Global SAC',
            'rating': 5,
            'comment': 'Entrega puntual, repuesto bien embalado y seguimiento claro durante todo el proceso.',
            'total': Decimal('189.90'),
            'days_ago': 18,
        },
        {
            'customer_username': 'cliente_jperez',
            'provider_name': 'Frenos y Seguridad Prudent Sac',
            'rating': 4,
            'comment': 'Buen trato y stock real. Solo faltó mayor detalle técnico en la confirmación inicial.',
            'total': Decimal('248.40'),
            'days_ago': 11,
        },
        {
            'customer_username': 'cliente_mlopez',
            'provider_name': 'Repuestos Premium Perú',
            'rating': 5,
            'comment': 'El producto llegó exactamente como en la publicación y el soporte postventa respondió rápido.',
            'total': Decimal('320.00'),
            'days_ago': 15,
        },
        {
            'customer_username': 'cliente_mlopez',
            'provider_name': 'Accesorios Axel',
            'rating': 4,
            'comment': 'Compra simple y confiable. Volvería a pedir con este proveedor.',
            'total': Decimal('96.50'),
            'days_ago': 7,
        },
        {
            'customer_username': 'cliente_flores_fleet',
            'provider_name': 'Distribuidora de Motores Morcano Sac',
            'rating': 5,
            'comment': 'Proveedor serio para compras B2B. Cumplió plazos y despacho de varias unidades sin incidencias.',
            'total': Decimal('1450.00'),
            'days_ago': 24,
        },
        {
            'customer_username': 'cliente_flores_fleet',
            'provider_name': 'Sistemas de Suspensión SS Sac',
            'rating': 4,
            'comment': 'Buen nivel técnico y comunicación clara. Mejoraría solo el detalle de guía de instalación.',
            'total': Decimal('870.30'),
            'days_ago': 10,
        },
        {
            'customer_username': 'cliente_taller_norte',
            'provider_name': 'Filtros y Aceites Técnicos El Father Sac',
            'rating': 5,
            'comment': 'Muy consistente en stock y calidad. Ideal para reposición frecuente del taller.',
            'total': Decimal('410.20'),
            'days_ago': 14,
        },
        {
            'customer_username': 'cliente_taller_norte',
            'provider_name': 'Electrónica Automotriz Techno Plus',
            'rating': 3,
            'comment': 'La pieza llegó bien, pero la comunicación fue más lenta que con otros proveedores.',
            'total': Decimal('535.90'),
            'days_ago': 6,
        },
        {
            'customer_username': 'cliente_retail_sur',
            'provider_name': 'Neumáticos Meca Express',
            'rating': 4,
            'comment': 'Proveedor ordenado y con despacho razonable. El catálogo coincide con lo recibido.',
            'total': Decimal('690.00'),
            'days_ago': 13,
        },
        {
            'customer_username': 'cliente_retail_sur',
            'provider_name': 'Talleres y Repuestos Arkham Sac',
            'rating': 5,
            'comment': 'Muy buena experiencia de compra. Atención rápida y comprobante emitido sin fricción.',
            'total': Decimal('275.80'),
            'days_ago': 5,
        },
    ]

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('▶ Iniciando carga de reseñas de prueba...'))

        created_reviews = 0
        updated_reviews = 0
        created_orders = 0
        created_suborders = 0

        for index, blueprint in enumerate(self.REVIEW_BLUEPRINTS, start=1):
            customer = self._get_customer(blueprint['customer_username'])
            provider = self._get_provider(blueprint['provider_name'])
            shipping_address = customer.addresses.order_by('-is_default', 'id').first()
            timestamp = timezone.now() - timezone.timedelta(days=blueprint['days_ago'])

            order_number = f"SEEDREV-{timezone.now().year}-{index:04d}"
            order, order_created = Order.objects.get_or_create(
                order_number=order_number,
                defaults={
                    'customer': customer,
                    'status': 'completado',
                    'delivery_method': 'domicilio',
                    'shipping_address': shipping_address,
                    'subtotal': blueprint['total'],
                    'discount': Decimal('0.00'),
                    'tax': Decimal('0.00'),
                    'total': blueprint['total'],
                    'customer_notes': 'Orden de prueba generada por seed_reviews.',
                    'payment_deadline': timestamp,
                },
            )
            if order_created:
                created_orders += 1
            else:
                order.customer = customer
                order.status = 'completado'
                order.delivery_method = 'domicilio'
                order.shipping_address = shipping_address
                order.subtotal = blueprint['total']
                order.discount = Decimal('0.00')
                order.tax = Decimal('0.00')
                order.total = blueprint['total']
                order.customer_notes = 'Orden de prueba generada por seed_reviews.'
                order.payment_deadline = timestamp
                order.save(update_fields=[
                    'customer', 'status', 'delivery_method', 'shipping_address',
                    'subtotal', 'discount', 'tax', 'total', 'customer_notes',
                    'payment_deadline', 'updated_at'
                ])

            sub_order_number = f"{order_number}-A"
            sub_order, sub_created = SubOrder.objects.get_or_create(
                sub_order_number=sub_order_number,
                defaults={
                    'order': order,
                    'provider': provider,
                    'status': 'entregado',
                    'subtotal': blueprint['total'],
                    'discount_percent': Decimal('0.00'),
                    'discount': Decimal('0.00'),
                    'igv_rate': Decimal('18.00') if provider.igv_applicable else Decimal('0.00'),
                    'igv_amount': Decimal('0.00'),
                    'total': blueprint['total'],
                    'payment_rejected': False,
                    'expired': False,
                    'refunded': False,
                    'confirmed_at': timestamp - timezone.timedelta(days=1),
                    'shipped_at': timestamp - timezone.timedelta(hours=12),
                    'delivered_at': timestamp,
                    'tracking_number': f'TRACK-SEED-{index:04d}',
                },
            )
            if sub_created:
                created_suborders += 1
            else:
                sub_order.order = order
                sub_order.provider = provider
                sub_order.status = 'entregado'
                sub_order.subtotal = blueprint['total']
                sub_order.discount_percent = Decimal('0.00')
                sub_order.discount = Decimal('0.00')
                sub_order.igv_rate = Decimal('18.00') if provider.igv_applicable else Decimal('0.00')
                sub_order.igv_amount = Decimal('0.00')
                sub_order.total = blueprint['total']
                sub_order.payment_rejected = False
                sub_order.expired = False
                sub_order.refunded = False
                sub_order.confirmed_at = timestamp - timezone.timedelta(days=1)
                sub_order.shipped_at = timestamp - timezone.timedelta(hours=12)
                sub_order.delivered_at = timestamp
                sub_order.tracking_number = f'TRACK-SEED-{index:04d}'
                sub_order.save(update_fields=[
                    'order', 'provider', 'status', 'subtotal', 'discount_percent',
                    'discount', 'igv_rate', 'igv_amount', 'total', 'payment_rejected',
                    'expired', 'refunded', 'confirmed_at', 'shipped_at', 'delivered_at',
                    'tracking_number', 'updated_at'
                ])

            review, review_created = ProviderReview.objects.get_or_create(
                customer=customer,
                sub_order=sub_order,
                defaults={
                    'provider': provider,
                    'rating': blueprint['rating'],
                    'comment': blueprint['comment'],
                    'status': ProviderReviewStatusChoices.PUBLISHED,
                    'is_visible': True,
                    'is_verified_purchase': True,
                },
            )
            if review_created:
                created_reviews += 1
            else:
                review.provider = provider
                review.rating = blueprint['rating']
                review.comment = blueprint['comment']
                review.status = ProviderReviewStatusChoices.PUBLISHED
                review.is_visible = True
                review.is_verified_purchase = True
                review.save(update_fields=[
                    'provider', 'rating', 'comment', 'status',
                    'is_visible', 'is_verified_purchase', 'updated_at'
                ])
                updated_reviews += 1

            provider.recalculate_rating_summary()
            self.stdout.write(
                f"✓ Review {review.id} | {customer.user.username} → {provider.name} ({review.rating}/5)"
            )

        self.stdout.write(self.style.SUCCESS(
            '✓ Seed reviews completado: '
            f'{created_orders} órdenes nuevas, '
            f'{created_suborders} subórdenes nuevas, '
            f'{created_reviews} reviews nuevas, '
            f'{updated_reviews} reviews actualizadas.'
        ))

    def _get_customer(self, username: str) -> Customer:
        try:
            return Customer.objects.select_related('user').get(user__username=username)
        except Customer.DoesNotExist as exc:
            raise CommandError(
                f"No existe Customer para el usuario '{username}'. Ejecuta seed_customers primero."
            ) from exc

    def _get_provider(self, name: str) -> Provider:
        normalized_name = ' '.join(name.split())

        try:
            return Provider.objects.get(name=normalized_name)
        except Provider.DoesNotExist as exc:
            provider = next(
                (
                    item for item in Provider.objects.all()
                    if ' '.join(item.name.split()) == normalized_name
                ),
                None,
            )
            if provider:
                return provider

            raise CommandError(
                f"No existe Provider '{name}'. Ejecuta seed_marketplace primero."
            ) from exc
