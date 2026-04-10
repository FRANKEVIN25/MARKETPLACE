"""
Signals de Products.

total_stock_cached se actualiza directamente por el sync de Odoo
(sync/tasks.py y management/commands/sync_products.py).
No hay señales de StockItem porque ese modelo fue eliminado.
Este archivo se mantiene para futura extensión si se necesita.
"""
