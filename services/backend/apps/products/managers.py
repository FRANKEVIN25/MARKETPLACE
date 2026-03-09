from django.db import models


class ProductQuerySet(models.QuerySet):
    """
    QuerySet de Productos con reglas de negocio del marketplace
    """

    def active(self):
        """Productos activos"""
        return self.filter(is_active=True)

    def for_provider(self, provider):
        """
        Productos visibles para un proveedor específico
        (backend privado)
        """
        return self.filter(provider=provider)

    def for_marketplace(self):
        """
        Productos visibles públicamente en el marketplace
        REGLA DE ORO:
        - Producto activo
        - Proveedor activo
        - Proveedor aprobado
        """
        return self.filter(
            is_active=True,
            provider__is_active=True,
            provider__is_approved=True,
        )


class ProductManager(models.Manager):
    """
    Manager público del modelo Product
    """

    def get_queryset(self):
        return ProductQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def for_provider(self, provider):
        return self.get_queryset().for_provider(provider)

    def for_marketplace(self):
        return self.get_queryset().for_marketplace()