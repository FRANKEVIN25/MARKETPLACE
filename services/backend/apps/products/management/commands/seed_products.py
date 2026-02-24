from django.core.management.base import BaseCommand
from apps.marketplace.models import Provider
from apps.products.models import Category, Product, Warehouse, StockItem, CompatibilidadProducto
from apps.vehicles.models import VariantVehiculo
import random


class Command(BaseCommand):
    help = 'Carga datos de prueba para Categorías, Productos, Almacenes y Stock'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('▶ Iniciando carga de datos de productos...'))

        # 1. Crear Categorías de Autopartes
        self.stdout.write('\n📁 Creando categorías...')
        categories_data = [
            {'name': 'Motor y Transmisión', 'description': 'Componentes del motor, transmisión y sistemas relacionados'},
            {'name': 'Suspensión', 'description': 'Amortiguadores, resortes, brazos y componentes de suspensión'},
            {'name': 'Frenos', 'description': 'Pastillas, discos, cilindros y sistemas de frenado'},
            {'name': 'Neumáticos y Ruedas', 'description': 'Neumáticos, llantas y accesorios de ruedas'},
            {'name': 'Electrónica y Electricidad', 'description': 'Baterías, alternadores, motores eléctricos y componentes'},
            {'name': 'Filtros', 'description': 'Filtros de aire, aceite, combustible y otros filtros'},
            {'name': 'Sistema de Escape', 'description': 'Silenciadores, tubos y componentes de escape'},
            {'name': 'Accesorios Interiores', 'description': 'Tapicería, volantes, alfombrillas y accesorios internos'},
            {'name': 'Accesorios Exteriores', 'description': 'Espejo, manillas, molduras y accesorios externos'},
            {'name': 'Lubricantes y Fluidos', 'description': 'Aceites, refrigerantes y otros fluidos automotrices'},
        ]

        categories = {}
        for cat_data in categories_data:
            cat, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            categories[cat_data['name']] = cat
            status = '✓ Creada' if created else '✓ Existente'
            self.stdout.write(f'{status}: {cat.name}')

        # 2. Obtener proveedores
        self.stdout.write('\n🏭 Obteniendo proveedores...')
        providers = list(Provider.objects.filter(is_approved=True)[:10])
        if not providers:
            self.stdout.write(self.style.ERROR('✗ No hay proveedores disponibles. Ejecuta seed_marketplace.py primero.'))
            return

        self.stdout.write(f'✓ {len(providers)} proveedores encontrados')

        # 3. Crear Almacenes (2 por proveedor)
        self.stdout.write('\n🏢 Creando almacenes...')
        warehouses = []
        for provider in providers:
            cities = ['Lima', 'Arequipa']
            for i, city in enumerate(cities, 1):
                warehouse, created = Warehouse.objects.get_or_create(
                    provider=provider,
                    name=f'{provider.name} - {city}',
                    defaults={
                        'city': city,
                        'address': f'Calle Principal {i}, {city}, Perú',
                        'is_active': True,
                    }
                )
                warehouses.append(warehouse)
                status = '✓ Creado' if created else '✓ Existente'
                self.stdout.write(f'{status}: {warehouse.name}')

        # 4. Crear Productos (10 productos)
        self.stdout.write('\n📦 Creando productos...')
        products_data = [
            {
                'name': 'Filtro de Aire Premium',
                'reference': 'AIR-FILTER-001',
                'category': 'Filtros',
                'price': 45.00,
                'description': 'Filtro de aire de alta calidad para motores',
                'manufacturer_code': 'AFM-2024-001',
            },
            {
                'name': 'Pastilla de Freno Frontal',
                'reference': 'BRAKE-PAD-001',
                'category': 'Frenos',
                'price': 85.00,
                'description': 'Pastillas de freno frontal con material cerámico',
                'manufacturer_code': 'BPF-2024-001',
            },
            {
                'name': 'Aceite Motor 5W-40 1L',
                'reference': 'OIL-MOTOR-001',
                'category': 'Lubricantes y Fluidos',
                'price': 35.00,
                'description': 'Aceite sintético premium 5W-40',
                'manufacturer_code': 'OIL-5W40-001',
            },
            {
                'name': 'Amortiguador Trasero',
                'reference': 'SHOCK-REAR-001',
                'category': 'Suspensión',
                'price': 220.00,
                'description': 'Amortiguador trasero hidráulico',
                'manufacturer_code': 'SHK-REAR-001',
            },
            {
                'name': 'Batería Automotriz 12V 60Ah',
                'reference': 'BATTERY-60AH',
                'category': 'Electrónica y Electricidad',
                'price': 350.00,
                'description': 'Batería automotriz de 60 amperios',
                'manufacturer_code': 'BAT-60AH-001',
            },
            {
                'name': 'Correa de Distribución',
                'reference': 'TIMING-BELT-001',
                'category': 'Motor y Transmisión',
                'price': 120.00,
                'description': 'Correa de distribución para motores',
                'manufacturer_code': 'TIM-BELT-001',
            },
            {
                'name': 'Disco de Freno 260mm',
                'reference': 'BRAKE-DISC-260',
                'category': 'Frenos',
                'price': 95.00,
                'description': 'Disco de freno ventilado 260mm',
                'manufacturer_code': 'BRK-DISC-260',
            },
            {
                'name': 'Tubo de Escape Inoxidable',
                'reference': 'EXHAUST-PIPE-001',
                'category': 'Sistema de Escape',
                'price': 180.00,
                'description': 'Tubo de escape en acero inoxidable',
                'manufacturer_code': 'EXH-PIPE-001',
            },
            {
                'name': 'Filtro de Combustible',
                'reference': 'FUEL-FILTER-001',
                'category': 'Filtros',
                'price': 55.00,
                'description': 'Filtro de combustible para inyección',
                'manufacturer_code': 'FUL-FILTER-001',
            },
            {
                'name': 'Bujía Iridio',
                'reference': 'SPARK-PLUG-IRID',
                'category': 'Electrónica y Electricidad',
                'price': 28.00,
                'description': 'Bujía de iridio de larga duración',
                'manufacturer_code': 'SPK-IRID-001',
            },
        ]

        products = []
        product_idx = 0
        for provider in providers:
            for prod_data in products_data[:1]:  # 1 producto por proveedor, 10 totales
                product_idx += 1
                
                prod, created = Product.objects.get_or_create(
                    provider=provider,
                    reference=f"{prod_data['reference']}-{product_idx}",
                    defaults={
                        'name': f"{prod_data['name']} v{product_idx}",
                        'category': categories[prod_data['category']],
                        'price': prod_data['price'],
                        'description': prod_data['description'],
                        'manufacturer_code': f"{prod_data['manufacturer_code']}-{product_idx}",
                        'tax_percent': 18.00,
                        'active': True,
                        'product_type': 'product',
                    }
                )
                products.append(prod)
                status = '✓ Creado' if created else '✓ Existente'
                self.stdout.write(f'{status}: {prod.name} ({provider.name})')

        # 5. Crear Compatibilidades (20 relaciones entre productos y variantes)
        self.stdout.write('\n🔗 Creando compatibilidades...')
        variants = list(VariantVehiculo.objects.all()[:20])
        
        if not variants:
            self.stdout.write(self.style.WARNING('⚠ No hay variantes de vehículos. Ejecuta seed.py en vehicles primero.'))
        else:
            compatibilities_created = 0
            for i, product in enumerate(products):
                # Asignar 2 variantes por producto
                variant_selection = variants[i*2:(i+1)*2]
                if not variant_selection:
                    variant_selection = [random.choice(variants)]
                
                for variant in variant_selection:
                    compat, created = CompatibilidadProducto.objects.get_or_create(
                        producto=product,
                        variante=variant,
                        defaults={'notas_instalacion': ''}
                    )
                    if created:
                        compatibilities_created += 1
                        self.stdout.write(f'✓ {product.name} → {variant}')
            
            self.stdout.write(f'✓ {compatibilities_created} compatibilidades creadas')

        # 6. Crear Stock Items
        self.stdout.write('\n📊 Creando stock items...')
        stock_created = 0
        for product in products:
            # Stock para cada almacén del proveedor
            product_warehouses = product.provider.warehouses.all()
            for warehouse in product_warehouses:
                quantity = random.randint(5, 100)
                stock, created = StockItem.objects.get_or_create(
                    product=product,
                    warehouse=warehouse,
                    defaults={'quantity': quantity}
                )
                if created:
                    stock_created += 1
                    self.stdout.write(f'✓ {product.name} → {warehouse.name}: {quantity} uds')

        self.stdout.write(self.style.SUCCESS(f'\n✓ Carga completada:'))
        self.stdout.write(f'  • {len(categories)} categorías')
        self.stdout.write(f'  • {len(warehouses)} almacenes')
        self.stdout.write(f'  • {len(products)} productos')
        self.stdout.write(f'  • {stock_created} registros de stock')
