from apps.marketplace.models import Provider
from apps.products.models import Product

providers = Provider.objects.filter(name__in=['Accesorios Axel', 'Electrónica Automotriz Techno Plus'])
correct_ids = {
    'Accesorios Axel': 2,
    'Electrónica Automotriz Techno Plus': 3,
}

for provider in providers:
    real_id = correct_ids[provider.name]

    odoo_products = conn.execute_kw(
        'product.template', 'search_read',
        [[['active', '=', True], ['company_id', '=', real_id]]],
        {
            'fields': [
                'id', 'name', 'default_code', 'description_sale',
                'list_price', 'type', 'company_id'
            ],
            'limit': 20
        }
    )

    print(f"\n🏢 {provider.name} (Odoo ID={real_id}) — {len(odoo_products)} producto(s):")
    for op in odoo_products:
        print(f"   [{op['id']}] {op['name']} | SKU: {op.get('default_code') or '—'} | Precio: {op['list_price']}")

        product, created = Product.objects.update_or_create(
            odoo_id=op['id'],
            provider=provider,
            defaults={
                'name': op['name'],
                'reference': op.get('default_code') or f"ODOO-{op['id']}",
                'price': op['list_price'],
                'description': op.get('description_sale') or '',
                'product_type': op.get('type', 'product'),
                'odoo_state': 'synced',
                'is_active': True,
            }
        )
        action = "✅ Creado" if created else "🔄 Actualizado"
        print(f"      {action} en Django → ID={product.id}")

print("\n🚀 Listo.")

#El siguiente codigo es para actualizar el stock de cada producto, configura previmiante el #stock a mano, almecenes y localizacion de cada producto en odoo.


from apps.products.models import Warehouse, StockItem, Product
from apps.marketplace.models import Provider

providers = Provider.objects.filter(name__in=['Accesorios Axel', 'Electrónica Automotriz Techno Plus'])
correct_ids = {'Accesorios Axel': 2, 'Electrónica Automotriz Techno Plus': 3}

for provider in providers:
    real_id = correct_ids[provider.name]

    # ── 1. Almacenes de Odoo para esta company ──────────────────────────────
    odoo_warehouses = conn.execute_kw(
        'stock.warehouse', 'search_read',
        [[['company_id', '=', real_id]]],
        {'fields': ['id', 'name', 'lot_stock_id']}
    )
    print(f"\n🏭 {provider.name} → {len(odoo_warehouses)} almacén(es) en Odoo")

    for ow in odoo_warehouses:
        warehouse, created = Warehouse.objects.update_or_create(
            odoo_warehouse_id=ow['id'],
            provider=provider,
            defaults={'name': ow['name'], 'is_active': True}
        )
        print(f"  {'✅ Creado' if created else '🔄 Actualizado'}: {warehouse.name} (Django ID={warehouse.id})")

        # lot_stock_id es la ubicación principal de almacenaje del warehouse
        stock_location_id = ow['lot_stock_id'][0] if ow.get('lot_stock_id') else None
        if not stock_location_id:
            print(f"  ⚠️  Sin lot_stock_id para {ow['name']}, omitiendo stock")
            continue

        # ── 2. Para cada producto del provider, buscar stock en esa ubicación ─
        provider_products = Product.objects.filter(provider=provider, odoo_id__isnull=False)
        print(f"  📦 Procesando stock de {provider_products.count()} productos...")

        for product in provider_products:
            # stock.quant filtra por template vía relación: product_id.product_tmpl_id
            quants = conn.execute_kw(
                'stock.quant', 'search_read',
                [[
                    ['product_id.product_tmpl_id', '=', product.odoo_id],
                    ['location_id', '=', stock_location_id],
                ]],
                {'fields': ['quantity', 'reserved_quantity']}
            )

            # Cantidad disponible = quantity - reserved_quantity
            available = sum(
                max(q['quantity'] - q.get('reserved_quantity', 0), 0)
                for q in quants
            )

            stock_item, si_created = StockItem.objects.update_or_create(
                product=product,
                warehouse=warehouse,
                defaults={'quantity': int(available)}
            )
            action = "✅" if si_created else "🔄"
            print(f"    {action} {product.name} → {int(available)} uds")

print("\n🚀 Stock importado.")