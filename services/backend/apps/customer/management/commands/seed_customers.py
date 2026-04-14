from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.customer.models import Address, Customer, CustomerStats


class Command(BaseCommand):
    help = 'Carga clientes de prueba con perfil, stats y dirección base.'

    CUSTOMERS = [
        {
            'username': 'cliente_jperez',
            'email': 'juan.perez@example.com',
            'first_name': 'Juan',
            'last_name': 'Perez',
            'customer_type': 'individual',
            'document_type': 'DNI',
            'document_number': '71456328',
            'phone': '999111222',
            'address': {
                'contact_name': 'Juan Perez',
                'contact_phone': '999111222',
                'street': 'Av. Javier Prado Este',
                'street_number': '1450',
                'district': 'San Isidro',
                'city': 'Lima',
                'state': 'Lima',
                'reference': 'Torre empresarial, piso 4',
            },
        },
        {
            'username': 'cliente_mlopez',
            'email': 'maria.lopez@example.com',
            'first_name': 'Maria',
            'last_name': 'Lopez',
            'customer_type': 'individual',
            'document_type': 'DNI',
            'document_number': '70234561',
            'phone': '998222333',
            'address': {
                'contact_name': 'Maria Lopez',
                'contact_phone': '998222333',
                'street': 'Calle Las Magnolias',
                'street_number': '255',
                'district': 'Miraflores',
                'city': 'Lima',
                'state': 'Lima',
                'reference': 'Casa color blanco',
            },
        },
        {
            'username': 'cliente_flores_fleet',
            'email': 'compras@floresfleet.pe',
            'first_name': 'Carlos',
            'last_name': 'Flores',
            'customer_type': 'company',
            'document_type': 'RUC',
            'document_number': '20604567891',
            'phone': '997333444',
            'company_name': 'Flores Fleet SAC',
            'business_activity': 'fleet',
            'address': {
                'contact_name': 'Carlos Flores',
                'contact_phone': '997333444',
                'street': 'Av. Trapiche',
                'street_number': '880',
                'district': 'Comas',
                'city': 'Lima',
                'state': 'Lima',
                'reference': 'Al costado del grifo',
            },
        },
        {
            'username': 'cliente_taller_norte',
            'email': 'admin@tallernorte.pe',
            'first_name': 'Rosa',
            'last_name': 'Guzman',
            'customer_type': 'company',
            'document_type': 'RUC',
            'document_number': '20555666771',
            'phone': '996444555',
            'company_name': 'Taller Norte Diesel SAC',
            'business_activity': 'workshop',
            'address': {
                'contact_name': 'Rosa Guzman',
                'contact_phone': '996444555',
                'street': 'Av. Industrial',
                'street_number': '120',
                'district': 'Independencia',
                'city': 'Lima',
                'state': 'Lima',
                'reference': 'Frente al mercado central',
            },
        },
        {
            'username': 'cliente_retail_sur',
            'email': 'retail@surparts.pe',
            'first_name': 'Luis',
            'last_name': 'Santos',
            'customer_type': 'company',
            'document_type': 'RUC',
            'document_number': '20444555671',
            'phone': '995555666',
            'company_name': 'Sur Parts Store EIRL',
            'business_activity': 'retail_store',
            'address': {
                'contact_name': 'Luis Santos',
                'contact_phone': '995555666',
                'street': 'Av. Los Heroes',
                'street_number': '610',
                'district': 'San Juan de Miraflores',
                'city': 'Lima',
                'state': 'Lima',
                'reference': 'Galeria automotriz, stand 12',
            },
        },
    ]

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('▶ Iniciando carga de customers de prueba...'))

        for raw_customer_data in self.CUSTOMERS:
            customer_data = dict(raw_customer_data)
            address_data = dict(customer_data.pop('address'))
            username = customer_data['username']
            email = customer_data['email']

            user, user_created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': customer_data['first_name'],
                    'last_name': customer_data['last_name'],
                },
            )
            if user_created:
                user.set_password('customer123')
                user.save(update_fields=['password'])
            else:
                updated = False
                if user.email != email:
                    user.email = email
                    updated = True
                if user.first_name != customer_data['first_name']:
                    user.first_name = customer_data['first_name']
                    updated = True
                if user.last_name != customer_data['last_name']:
                    user.last_name = customer_data['last_name']
                    updated = True
                if updated:
                    user.save(update_fields=['email', 'first_name', 'last_name'])

            customer_defaults = {
                'customer_type': customer_data['customer_type'],
                'document_type': customer_data['document_type'],
                'document_number': customer_data['document_number'],
                'phone': customer_data['phone'],
                'company_name': customer_data.get('company_name', ''),
                'business_activity': customer_data.get('business_activity', ''),
                'is_active': True,
                'is_verified': True,
            }
            customer, created = Customer.objects.get_or_create(
                user=user,
                defaults=customer_defaults,
            )
            if not created:
                changed_fields = []
                for field, value in customer_defaults.items():
                    if getattr(customer, field) != value:
                        setattr(customer, field, value)
                        changed_fields.append(field)
                if changed_fields:
                    customer.save(update_fields=changed_fields + ['updated_at'])

            CustomerStats.objects.get_or_create(customer=customer)

            Address.objects.get_or_create(
                customer=customer,
                address_type='shipping',
                street=address_data['street'],
                street_number=address_data.get('street_number', ''),
                defaults={
                    'contact_name': address_data['contact_name'],
                    'contact_phone': address_data['contact_phone'],
                    'district': address_data['district'],
                    'city': address_data['city'],
                    'state': address_data['state'],
                    'country': 'Perú',
                    'reference': address_data.get('reference', ''),
                    'is_default': True,
                },
            )

            state = '✓ Creado' if created else '✓ Actualizado'
            self.stdout.write(f"{state}: {customer.get_full_name()} ({user.username})")

        self.stdout.write(self.style.SUCCESS(f'✓ Seed completado: {len(self.CUSTOMERS)} customers listos'))
