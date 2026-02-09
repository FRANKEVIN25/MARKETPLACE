#!/usr/bin/env python3
"""
Script para inicializar Odoo:
1. Crear Provider en Django
2. Crear Company en Odoo
3. Vincular Provider con Company
4. Crear producto de prueba
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecomparts.settings')
django.setup()

from apps.marketplace.models import Provider
from apps.sync.odoo_connector import OdooConnector
from django.conf import settings


def main():
    print("=" * 70)
    print("🏗️  SETUP INICIAL: Crear primera Company en Odoo")
    print("=" * 70)
    
    # ==========================================
    # PASO 1: Crear/Verificar Provider en Django
    # ==========================================
    print("\n📌 PASO 1: Provider en Django")
    print("-" * 70)
    
    provider_data = {
        'name': 'AutoPartes Demo SAC',
        'ruc': '20123456789',
        'email': 'demo@autopartes.pe',
        'phone': '+51 999 888 777',
        'tier': 'starter',
        'is_active': True,
        'is_approved': True,
    }
    
    # Obtener el owner (primer superuser)
    from django.contrib.auth.models import User
    owner = User.objects.filter(is_superuser=True).first()
    
    if not owner:
        print("❌ ERROR: No existe ningún superuser. Crea uno con:")
        print("   docker exec -it ecomparts-backend python manage.py createsuperuser")
        return
    
    provider_data['owner'] = owner
    
    provider, created = Provider.objects.get_or_create(
        ruc=provider_data['ruc'],
        defaults=provider_data
    )
    
    if created:
        print(f"✅ Provider creado: {provider.name}")
    else:
        print(f"ℹ️  Provider ya existe: {provider.name}")
    
    print(f"   📝 RUC: {provider.ruc}")
    print(f"   📧 Email: {provider.email}")
    print(f"   🎚️  Tier: {provider.get_tier_display()}")
    
    # ==========================================
    # PASO 2: Conectar con Odoo
    # ==========================================
    print("\n📌 PASO 2: Conexión con Odoo")
    print("-" * 70)
    
    try:
        odoo = OdooConnector(
            url=settings.ODOO_URL,
            db_name=settings.ODOO_DB,
            username=settings.ODOO_USERNAME,
            password=settings.ODOO_PASSWORD
        )
        print(f"✅ Conectado a Odoo")
        print(f"   🌐 URL: {settings.ODOO_URL}")
        print(f"   💾 Base de datos: {settings.ODOO_DB}")
        print(f"   👤 Usuario: {settings.ODOO_USERNAME} (UID: {odoo.uid})")
    except Exception as e:
        print(f"❌ ERROR al conectar con Odoo: {e}")
        print("\nVerifica que Odoo esté corriendo:")
        print("   docker-compose ps")
        return
    
    # ==========================================
    # PASO 3: Crear Company en Odoo
    # ==========================================
    print("\n📌 PASO 3: Company en Odoo")
    print("-" * 70)
    
    # Verificar si ya existe
    existing_companies = odoo.search_read(
        'res.company',
        domain=[('vat', '=', provider.ruc)],
        fields=['id', 'name', 'vat'],
        limit=1
    )
    
    if existing_companies:
        odoo_company_id = existing_companies[0]['id']
        print(f"ℹ️  Company ya existe en Odoo (ID: {odoo_company_id})")
    else:
        # Crear company
        company_vals = {
            'name': provider.name,
            'vat': provider.ruc,
            'email': provider.email,
            'phone': provider.phone,
            'currency_id': 149,  # PEN (Soles Peruanos)
            'country_id': 173,   # Perú
        }
        
        try:
            odoo_company_id = odoo.create('res.company', company_vals)
            print(f"✅ Company creada en Odoo (ID: {odoo_company_id})")
        except Exception as e:
            print(f"❌ ERROR al crear company: {e}")
            return
    
    # Actualizar Provider con odoo_company_id
    provider.odoo_company_id = odoo_company_id
    provider.save(update_fields=['odoo_company_id'])
    print(f"✅ Provider actualizado con odoo_company_id: {odoo_company_id}")
    
    # Verificar la company
    company_info = odoo.search_read(
        'res.company',
        domain=[('id', '=', odoo_company_id)],
        fields=['name', 'vat', 'email', 'currency_id'],
        limit=1
    )[0]
    
    print(f"\n   📊 Datos de la Company en Odoo:")
    print(f"      ID: {company_info['id']}")
    print(f"      Nombre: {company_info['name']}")
    print(f"      RUC: {company_info.get('vat', 'N/A')}")
    print(f"      Email: {company_info.get('email', 'N/A')}")
    print(f"      Moneda: {company_info['currency_id'][1]}")
    
    # ==========================================
    # PASO 4: Crear producto de prueba
    # ==========================================
    print("\n📌 PASO 4: Producto de prueba en Odoo")
    print("-" * 70)
    
    # Verificar si ya existe
    existing_products = odoo.search_read(
        'product.product',
        domain=[
            ('company_id', '=', odoo_company_id),
            ('default_code', '=', 'DEMO-FO-001')
        ],
        fields=['id', 'name'],
        limit=1
    )
    
    if existing_products:
        product_id = existing_products[0]['id']
        print(f"ℹ️  Producto de prueba ya existe (ID: {product_id})")
    else:
        # Crear producto
        product_vals = {
            'name': 'Filtro de Aceite Universal - Demo',
            'default_code': 'DEMO-FO-001',
            'type': 'product',
            'list_price': 45.00,
            'standard_price': 30.00,
            'barcode': '7501234567890',
            'company_id': odoo_company_id,
            'sale_ok': True,
            'purchase_ok': True,
            'active': True,
        }
        
        try:
            product_id = odoo.create('product.product', product_vals)
            print(f"✅ Producto de prueba creado (ID: {product_id})")
        except Exception as e:
            print(f"❌ ERROR al crear producto: {e}")
            product_id = None
    
    if product_id:
        # Verificar el producto
        product_info = odoo.search_read(
            'product.product',
            domain=[('id', '=', product_id)],
            fields=['name', 'default_code', 'list_price', 'qty_available', 'barcode'],
            limit=1
        )[0]
        
        print(f"\n   📦 Datos del Producto:")
        print(f"      ID: {product_info['id']}")
        print(f"      Nombre: {product_info['name']}")
        print(f"      SKU: {product_info.get('default_code', 'N/A')}")
        print(f"      Precio: S/ {product_info['list_price']:.2f}")
        print(f"      Stock: {product_info.get('qty_available', 0)}")
        print(f"      Código de barras: {product_info.get('barcode', 'N/A')}")
    
    # ==========================================
    # RESUMEN FINAL
    # ==========================================
    print("\n" + "=" * 70)
    print("✅ SETUP COMPLETADO EXITOSAMENTE")
    print("=" * 70)
    
    print(f"\n🎯 Próximos pasos:")
    print(f"\n1. Accede a Odoo:")
    print(f"   URL: http://localhost:8070")
    print(f"   Usuario: {settings.ODOO_USERNAME}")
    print(f"   Password: {settings.ODOO_PASSWORD}")
    
    print(f"\n2. Sincroniza productos al marketplace:")
    print(f"   docker exec -it ecomparts-backend python manage.py sync_products --provider-id {provider.id}")
    
    print(f"\n3. O sincroniza todos los providers:")
    print(f"   docker exec -it ecomparts-backend python manage.py sync_products")
    
    print(f"\n4. Accede al Django Admin:")
    print(f"   URL: http://localhost:8000/admin")
    print(f"   Verifica el provider y los productos sincronizados")
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()