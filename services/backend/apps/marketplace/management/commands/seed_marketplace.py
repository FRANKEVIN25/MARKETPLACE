from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.marketplace.models import Provider, Member
import random


class Command(BaseCommand):
    help = 'Carga datos de prueba para Provider y Member'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('▶ Iniciando carga de datos de marketplace...'))

        # 1. Crear o obtener superuser para owner
        try:
            admin_user = User.objects.get(username='admin')
        except User.DoesNotExist:
            admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            self.stdout.write(self.style.WARNING(f'✓ Superuser creado: admin'))

        # 2. Datos de proveedores
        providers_data = [
            {
                'name': 'AutoPartes Global SAC',
                'ruc': '20123456789',
                'email': 'contacto@autopartesglobal.pe',
                'phone': '+51987654321',
                'is_approved': True,
            },
            {
                'name': 'Repuestos Premium Perú',
                'ruc': '20987654321',
                'email': 'ventas@repuestospremium.pe',
                'phone': '+51976543210',
                'is_approved': True,
            },
            {
                'name': 'Distribuidora de Motores Morcano Sac',
                'ruc': '20111222333',
                'email': 'info@distribuidoramotores.pe',
                'phone': '+51965432109',
                'is_approved': True,
            },
            {
                'name': 'Talleres y Repuestos Arkham Sac',
                'ruc': '20444555666',
                'email': 'contacto@Arkham.pe',
                'phone': '+51954321098',
                'is_approved': True,
            },
            {
                'name': 'Filtros y Aceites Técnicos El Father Sac',
                'ruc': '20777888999',
                'email': 'ventas@filtrosaceites.pe',
                'phone': '+51943210987',
                'is_approved': True,
            },
            {
                'name': 'Electrónica Automotriz Techno Plus ',
                'ruc': '20111333555',
                'email': 'electronica@automotrizplus.pe',
                'phone': '+51932109876',
                'is_approved': True,
            },
            {
                'name': 'Neumáticos Meca Express',
                'ruc': '20222444666',
                'email': 'ruedas@express.pe',
                'phone': '+51921098765',
                'is_approved': True,
            },
            {
                'name': 'Sistemas de Suspensión SS Sac',
                'ruc': '20333555777',
                'email': 'suspension@avanzado.pe',
                'phone': '+51910987654',
                'is_approved': True,
            },
            {
                'name': 'Frenos y Seguridad Prudent Sac',
                'ruc': '20444666888',
                'email': 'frenos@prudent.pe',
                'phone': '+51909876543',
                'is_approved': True,
            },
            {
                'name': 'Accesorios Axel',
                'ruc': '20555777999',
                'email': 'accesorios@axel.pe',
                'phone': '+51998765432',
                'is_approved': True,
            },
        ]

        providers_created = []
        for provider_data in providers_data:
            provider, created = Provider.objects.get_or_create(
                name=provider_data['name'],
                defaults={
                    'ruc': provider_data['ruc'],
                    'email': provider_data['email'],
                    'phone': provider_data['phone'],
                    'is_approved': provider_data['is_approved'],
                    'owner': admin_user,
                    'is_active': True,
                }
            )
            providers_created.append(provider)
            status = '✓ Creado' if created else '✓ Existente'
            self.stdout.write(f'{status}: {provider.name}')

        # 3. Crear un miembro por proveedor
        for provider in providers_created:
            # Crear usuario para el miembro
            username = f'{provider.slug}_admin'
            email = provider.email or f'{provider.slug}@example.com'
            
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password='member123',
                    first_name=provider.name.split()[0],
                    last_name='Admin'
                )

            # Crear membresía
            member, created = Member.objects.get_or_create(
                user=user,
                provider=provider,
                defaults={
                    'role': 'admin',
                    'can_manage_products': True,
                    'can_manage_prices': True,
                    'can_manage_stock': True,
                    'can_invite_users': True,
                    'can_sync_odoo': False,
                }
            )
            status = '✓ Creado' if created else '✓ Existente'
            self.stdout.write(f'  {status}: Miembro {username} en {provider.name}')

        self.stdout.write(self.style.SUCCESS(f'✓ Carga completada: {len(providers_created)} proveedores'))
