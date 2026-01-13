from django.apps import AppConfig


class CustomerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.customer'
    verbose_name = 'Clientes'
    
    def ready(self):
        """Import signals when app is ready"""
        # import apps.customer.signals  # Descomentar si creas signals después
        pass