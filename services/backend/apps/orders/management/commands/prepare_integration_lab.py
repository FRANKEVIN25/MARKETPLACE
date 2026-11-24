"""Prepare owned fixtures only. Orders themselves must go through the HTTP API."""

import json
import os
import secrets
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.customer.models import Customer
from apps.marketplace.models import Provider
from apps.products.models import Product
from apps.sync.odoo_connector import OdooConnector


class Command(BaseCommand):
    help = 'Prepara fixtures A/B/C del proyecto local ecomparts-lab-integration'

    def add_arguments(self, parser):
        parser.add_argument('--fresh-customer', action='store_true')

    def handle(self, *args, **options):
        if (os.environ.get('LAB_MODE') != '1' or not settings.DEBUG
                or os.environ.get('LAB_INTEGRATION_PROJECT') != 'ecomparts-lab-integration'):
            raise CommandError('Solo se permite en el proyecto de integracion aislado')
        password = os.environ.get('LAB_E2E_PASSWORD')
        if not password:
            raise CommandError('Falta LAB_E2E_PASSWORD generado localmente')
        vendor_prefix = os.environ.get('LAB_E2E_ODOO_PASSWORD_PREFIX')
        if not vendor_prefix:
            raise CommandError('Falta el prefijo de credenciales de los usuarios LAB de Odoo')
        if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
            raise CommandError('La prueba requiere un worker Celery real')
        User = get_user_model()
        suffix = '_' + secrets.token_hex(4) if options['fresh_customer'] else ''
        customer_user, _ = User.objects.get_or_create(username='LAB_E2E_ANA'+suffix, defaults={
            'email': 'ana.e2e'+suffix+'@ecomparts.local', 'first_name': 'Ana', 'last_name': 'Prueba LAB'})
        customer_user.set_password(password)
        customer_user.is_active = True
        customer_user.save()
        customer, _ = Customer.objects.get_or_create(user=customer_user, defaults={'is_active': True})
        connector = OdooConnector()
        if not connector.uid:
            raise CommandError('No se pudo autenticar contra Odoo de Kubernetes')
        cases = []
        for letter in 'ABC':
            company = connector.execute_kw('res.company', 'search', [[['name', '=', f'LAB - Compania {letter}']]])
            if len(company) != 1:
                raise CommandError(f'Falta compania LAB {letter}')
            context = {'allowed_company_ids': company, 'company_id': company[0]}
            products = connector.execute_kw('product.product', 'search_read', [[
                ['name', '=', f'BENCH-{letter}-001'], ['company_id', '=', company[0]],
            ]], {'fields': ['id', 'name', 'list_price', 'qty_available'], 'context': context})
            vendor_ids = connector.execute_kw('res.users', 'search', [[['login', '=', f'lab-{letter.lower()}@ecomparts.local']]])
            if len(products) != 1 or not vendor_ids or products[0]['qty_available'] < 2:
                raise CommandError(f'Faltan producto, stock o usuario LAB {letter}')
            name = f'LAB-E2E-Proveedor-{letter}'
            existing = Provider.objects.filter(odoo_company_id=company[0]).first()
            if existing and existing.name != name:
                raise CommandError('No se modifica un proveedor ajeno al fixture LAB-E2E')
            owner, _ = User.objects.get_or_create(username='LAB_E2E_SELLER_'+letter)
            owner.set_unusable_password()
            owner.save()
            provider, _ = Provider.objects.get_or_create(name=name, defaults={'owner': owner})
            provider.odoo_company_id = company[0]
            provider.odoo_user_id = vendor_ids[0]
            provider.odoo_username = f'lab-{letter.lower()}@ecomparts.local'
            # Preserve the actual LAB vendor credential as a hash, as in normal provisioning.
            provider.set_odoo_password(vendor_prefix + '-' + letter)
            provider.is_active = provider.is_approved = True
            provider.save()
            remote = products[0]
            product, _ = Product.objects.update_or_create(provider=provider, reference='LAB-E2E-'+letter,
                defaults={'name': 'LAB-E2E-Filtro-'+letter, 'price': Decimal(str(remote['list_price'])),
                          'odoo_product_id': remote['id'], 'total_stock_cached': int(remote['qty_available']),
                          'is_active': True, 'is_published': True, 'es_universal': True, 'odoo_state': 'synced'})
            cases.append({'company': letter, 'company_id': company[0], 'product_id': product.id,
                          'odoo_product_id': remote['id'], 'provider_id': provider.id})
        self.stdout.write('LAB_FIXTURE_JSON:'+json.dumps({'username': customer_user.username,
            'customer_id': customer.id, 'celery_eager': False, 'cases': cases}))
