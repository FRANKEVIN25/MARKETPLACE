"""
Modelos de Productos - Versión MVP
"""
from django.db import models
from django.utils.text import slugify
from mptt.models import MPTTModel, TreeForeignKey


class Category(MPTTModel):
    """
    Categoría jerárquica de productos.
    UNIVERSAL - No tiene provider_group (compartida por todos)
    """
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class MPTTMeta:
        order_insertion_by = ['name']
    
    class Meta:
        db_table = 'products_category'
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ProductQuerySet(models.QuerySet):
    """QuerySet personalizado con filtros por tenant"""
    
    def for_group(self, group):
        """Filtrar productos por grupo"""
        if group:
            return self.filter(provider_group=group)
        return self.none()
    
    def for_marketplace(self):
        """Productos activos para el marketplace público"""
        return self.filter(
            active=True,
            provider_group__is_approved=True,
            provider_group__is_active=True
        )


class ProductManager(models.Manager):
    """Manager con soporte para multi-tenancy"""
    
    def get_queryset(self):
        return ProductQuerySet(self.model, using=self._db)
    
    def for_group(self, group):
        return self.get_queryset().for_group(group)
    
    def for_marketplace(self):
        return self.get_queryset().for_marketplace()


# Agregar en la clase Product:
# objects = ProductManager()
class Product(models.Model):
    """
    Producto de un proveedor específico.
    Cada producto pertenece a UN proveedor (provider_group).
    """
    PRODUCT_TYPE_CHOICES = [
        ('consu', 'Consumible'),
        ('service', 'Servicio'),
        ('product', 'Almacenable'),
    ]
    
    # 🔑 CAMPO CRÍTICO: Relación con el proveedor
    provider_group = models.ForeignKey(
        'marketplace.ProviderGroup',
        on_delete=models.CASCADE,
        related_name='products',
        help_text='Proveedor dueño de este producto'
    )
    
    # Identificación
    name = models.CharField(max_length=200)
    reference = models.CharField(
        max_length=50,
        db_index=True,
        help_text="SKU o referencia del consumidor"
    )
    slug = models.SlugField(max_length=255, blank=True, editable=False)
    
    # Tipo de producto
    product_type = models.CharField(
        max_length=10,
        choices=PRODUCT_TYPE_CHOICES,
        default='consu',
        help_text='Tipo de producto en Odoo'
    )
    
    # Códigos
    manufacturer_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Código interno del fabricante"
    )
    
    # Contenido
    image = models.ImageField(
        upload_to='products/',
        blank=True,
        null=True,
        help_text="Imagen principal del producto"
    )
    description = models.TextField(blank=True, null=True)
    
    # Precio
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Precio base"
    )
    
    # Categoría (UNIVERSAL - compartida)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )
    
    # Estado
    active = models.BooleanField(default=True)
    
    # Integración Odoo
    odoo_product_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="ID del producto en Odoo (product.product)"
    )
    odoo_template_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="ID de la plantilla en Odoo (product.template)"
    )
    last_synced_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProductManager() 
    
    class Meta:
        db_table = 'products_product'
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['-created_at']
        # Referencia única dentro del proveedor
        unique_together = [['provider_group', 'reference']]
        indexes = [
            models.Index(fields=['provider_group', 'active']),
            models.Index(fields=['reference']),
            models.Index(fields=['odoo_product_id']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.provider_group.name})"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            # Slug único: nombre-proveedor-id
            base_slug = slugify(self.name)
            self.slug = f"{base_slug}-{self.provider_group.slug}"
        super().save(*args, **kwargs)
    
    @property
    def is_synced(self):
        """Producto está sincronizado con Odoo"""
        return self.odoo_product_id is not None