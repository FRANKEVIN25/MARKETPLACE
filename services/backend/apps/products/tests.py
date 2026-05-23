from decimal import Decimal
from unittest.mock import Mock

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from rest_framework.test import APIRequestFactory

from apps.marketplace.models import Provider
from apps.products.admin import ProductAdmin
from apps.products.models import Category, Product
from apps.products.views import PublicCategoryListView


class ProductAdminActionsTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='product-admin-user',
            email='product-admin@example.com',
            password='testpass123',
        )
        self.provider = Provider.objects.create(
            name='Proveedor Admin',
            owner=self.user,
            is_active=True,
            is_approved=True,
        )
        self.request = RequestFactory().post('/admin/products/product/')
        self.request.user = self.user
        self.admin = ProductAdmin(Product, AdminSite())
        self.admin.message_user = Mock()

    def create_product(self, name: str, reference: str, is_published: bool = False) -> Product:
        return Product.objects.create(
            provider=self.provider,
            name=name,
            reference=reference,
            price=Decimal('100.00'),
            tax_percent=Decimal('18.00'),
            is_active=True,
            is_published=is_published,
            total_stock_cached=10,
        )

    def test_mark_as_published_updates_selected_products(self):
        draft_product = self.create_product('Producto borrador', 'SKU-DRAFT-001', is_published=False)
        published_product = self.create_product('Producto visible', 'SKU-PUB-001', is_published=True)

        queryset = Product.objects.filter(pk__in=[draft_product.pk, published_product.pk])

        self.admin.mark_as_published(self.request, queryset)

        draft_product.refresh_from_db()
        published_product.refresh_from_db()

        self.assertTrue(draft_product.is_published)
        self.assertTrue(published_product.is_published)
        self.admin.message_user.assert_called_once()

    def test_mark_as_unpublished_updates_selected_products(self):
        first_product = self.create_product('Producto 1', 'SKU-001', is_published=True)
        second_product = self.create_product('Producto 2', 'SKU-002', is_published=True)

        queryset = Product.objects.filter(pk__in=[first_product.pk, second_product.pk])

        self.admin.mark_as_unpublished(self.request, queryset)

        first_product.refresh_from_db()
        second_product.refresh_from_db()

        self.assertFalse(first_product.is_published)
        self.assertFalse(second_product.is_published)
        self.admin.message_user.assert_called_once()


class PublicCategoryListViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_public_categories_returns_hierarchical_tree_sorted_by_import_code(self):
        root_motor = Category.objects.create(name='Motor y Componentes Internos')
        root_frenos = Category.objects.create(name='Sistema de Frenos')

        sub_distribucion = Category.objects.create(name='Distribución', parent=root_motor)
        sub_admision = Category.objects.create(name='Admisión', parent=root_motor)
        leaf_correas = Category.objects.create(name='Correas y Cadenas', parent=sub_distribucion)
        leaf_tensores = Category.objects.create(name='Tensores y Poleas', parent=sub_distribucion)

        request = self.factory.get('/api/v1/products/public/categories/')
        response = PublicCategoryListView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['name'] for item in response.data], [
            'Motor y Componentes Internos',
            'Sistema de Frenos',
        ])

        motor = response.data[0]
        self.assertEqual([item['name'] for item in motor['children']], [
            'Distribución',
            'Admisión',
        ])
        self.assertEqual(motor['children_count'], 2)

        distribucion = motor['children'][0]
        self.assertEqual([item['name'] for item in distribucion['children']], [
            'Correas y Cadenas',
            'Tensores y Poleas',
        ])
        self.assertEqual(distribucion['children_count'], 2)
        self.assertEqual(distribucion['level'], 1)
        self.assertEqual(distribucion['children'][0]['level'], 2)

        self.assertEqual(leaf_correas.import_code, 'LEF001')
        self.assertEqual(leaf_tensores.import_code, 'LEF002')