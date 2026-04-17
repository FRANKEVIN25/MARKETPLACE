"""
apps/sync/services
==================
Lógica de negocio de sincronización Odoo ↔ Django.

Módulos:
  categories     — push_categories(): catálogo global Django → Odoo
  products       — sync_provider_catalog_snapshot(), sync_provider_product_images(), sync_provider_products(), sync_provider_stock()
  compatibility  — sync_provider_compatibility(), _resolve_django_variant()
  provisioning   — create_provider_with_odoo_setup(), verify_provider_odoo_connection()
  orders         — sync_suborder_to_odoo(), update_odoo_payment/delivery_status()

Todos los @shared_task en tasks.py son thin wrappers que llaman a estos servicios.
Las signals en orders/signals.py también delegan aquí.
"""
