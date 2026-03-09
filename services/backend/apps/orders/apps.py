from django.apps import AppConfig

class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.orders'
    verbose_name = 'Orders'
    
    def ready(self):
        """Conectar señales y registrar utilidades Odoo cuando Django esté listo."""
        import apps.orders.signals  # noqa: registra utilidades Odoo

        # Conectar post_save de SubOrder para recalcular Order.status derivado.
        # Se hace aquí (no con @receiver) para evitar importaciones circulares.
        from django.db.models.signals import post_save
        from .models import SubOrder
        from .signals import recalculate_order_status
        post_save.connect(recalculate_order_status, sender=SubOrder)
