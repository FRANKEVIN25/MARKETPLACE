from django.db import models


class ProductQuerySet(models.QuerySet):
    """
    QuerySet de Productos con reglas de negocio del marketplace
    """

    def active(self):
        """Productos activos (no eliminados lógicamente)."""
        return self.filter(is_active=True)

    def published(self):
        """Productos publicados (visibles al público, activos)."""
        return self.filter(is_active=True, is_published=True)

    def for_provider(self, provider):
        """
        Productos de un proveedor específico — backend privado.
        Incluye borradores (is_published=False).
        """
        return self.filter(provider=provider)

    def for_marketplace(self):
        """
        Productos visibles públicamente en el marketplace.
        REGLA DE ORO:
        - Producto activo Y publicado
        - Proveedor activo y aprobado
        """
        return self.filter(
            is_active=True,
            is_published=True,
            provider__is_active=True,
            provider__is_approved=True,
        )

    def with_stock(self, threshold=None):
        """
        Filtra productos con stock suficiente para venta.
        Acepta un threshold explícito; por defecto usa MIN_STOCK_THRESHOLD del modelo.
        """
        from apps.products.models import Product
        min_stock = threshold if threshold is not None else Product.MIN_STOCK_THRESHOLD
        return self.filter(total_stock_cached__gte=min_stock)


class ProductManager(models.Manager):
    """
    Manager público del modelo Product
    """

    def get_queryset(self):
        return ProductQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def published(self):
        return self.get_queryset().published()

    def for_provider(self, provider):
        return self.get_queryset().for_provider(provider)

    def for_marketplace(self):
        return self.get_queryset().for_marketplace()

    def with_stock(self, threshold=None):
        return self.get_queryset().with_stock(threshold)