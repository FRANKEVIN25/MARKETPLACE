"""
Modelos de Productos - Versión MVP
"""
from django.db import models
from django.utils.text import slugify
from mptt.models import MPTTModel, TreeForeignKey
from django.core.exceptions import ValidationError

class Category(MPTTModel):
    """
    Categoría jerárquica de productos.
    UNIVERSAL - No tiene provider (compartida por todos)
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
    
    def for_group(self, provider):
        """Filtrar productos por proveedor"""
        if provider:
            return self.filter(provider=provider)
        return self.none()
    
    def for_marketplace(self):
        """Productos activos para el marketplace público"""
        return self.filter(
            active=True,
            provider__is_approved=True,
            provider__is_active=True
        )


class ProductManager(models.Manager):
    """Manager con soporte para multi-tenancy"""
    
    def get_queryset(self):
        return ProductQuerySet(self.model, using=self._db)
    
    def for_group(self, provider):
        return self.get_queryset().for_group(provider)
    
    def for_marketplace(self):
        return self.get_queryset().for_marketplace()


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
    provider = models.ForeignKey(
        'marketplace.Provider',
        on_delete=models.CASCADE,
        related_name='products',
        help_text='Proveedor dueño de este producto'
    )
    
    # Identificación
    name = models.CharField(max_length=200)
    reference = models.CharField(max_length=50, db_index=True, help_text="SKU o referencia del consumidor")
    slug = models.SlugField(max_length=255, blank=True, editable=False)
    
    # Tipo de producto
    product_type = models.CharField(
        max_length=12,
        choices=PRODUCT_TYPE_CHOICES,
        default='product',
        help_text='Tipo de producto en Odoo'
    )
    
    # Códigos
    manufacturer_code = models.CharField(max_length=50, blank=True, null=True, help_text="Código del fabricante")
    
    # Contenido
    image = models.ImageField(
        upload_to='products/',
        blank=True,
        null=True,
        help_text="Imagen principal del producto"
    )

    description = models.TextField(blank=True, null=True)
    
    # Precio
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio base")
    
    # Categoría (UNIVERSAL - compartida)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )
    
    active = models.BooleanField(default=True)
    es_universal = models.BooleanField(default=False, db_index=True) # si es True no necesita compatibilidad

    vehiculos_compatibles = models.ManyToManyField(
        'vehicles.VariantVehiculo',
        through='CompatibilidadProducto',
        related_name='productos'
    )    

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
        unique_together = [['provider', 'reference']]
        indexes = [
            models.Index(fields=['provider', 'active']),
            models.Index(fields=['reference']),
            models.Index(fields=['odoo_product_id']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.provider.name})"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            # Slug único: nombre-proveedor-id
            base_slug = slugify(self.name)
            self.slug = f"{base_slug}-{self.provider.slug}"
        super().save(*args, **kwargs)
    
    @property
    def is_synced(self):
        """Producto está sincronizado con Odoo"""
        return self.odoo_product_id is not None
    

class CompatibilidadProducto(models.Model):
    producto = models.ForeignKey(Product, on_delete=models.CASCADE)
    variante = models.ForeignKey('vehicles.VariantVehiculo', on_delete=models.CASCADE)
    
    # Campo extra que te agradecerán en el futuro:
    notas_instalacion = models.CharField(max_length=255, blank=True, help_text="Ej: Solo aplica a frenos delanteros")

    class Meta:
        unique_together = ('producto', 'variante')
        indexes = [
            models.Index(fields=['variante', 'producto']),
        ]    

    def clean(self):
        provider = self.producto.provider
        from apps.vehicles.services.provider_variants import variantes_disponibles_para_proveedor
        if not variantes_disponibles_para_proveedor(provider).filter(
            id=self.variante_id
        ).exists():
            raise ValidationError(
                "Esta variante no está autorizada para este proveedor."
            )


