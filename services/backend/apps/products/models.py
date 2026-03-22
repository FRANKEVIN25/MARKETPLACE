"""
Modelos de Productos - Versión MVP
"""
from django.db import models
from django.utils.text import slugify
from mptt.models import MPTTModel, TreeForeignKey
from django.core.exceptions import ValidationError
from django.db.models import Sum
from .managers import ProductManager

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
    image_url = models.URLField(max_length=500, blank=True, null=True, help_text="URL de la imagen en Cloudinary/CDN")
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
    odoo_id = models.IntegerField(null=True, blank=True)
    odoo_state = models.CharField(
        max_length=20, 
        choices=[
            ('pending', 'Pendiente'),
            ('synced', 'Sincronizado'),
            ('failed', 'Fallido')
        ],
        default='pending'
    )
    
    # CAMPO CRÍTICO: Relación con el proveedor
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
    image_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="URL de la imagen en Cloudinary/CDN"
    )
    image_cloudinary_id = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Public ID en Cloudinary para transformaciones"
    )

    description = models.TextField(blank=True, null=True)
    
    # Precio (BASE IMPONIBLE)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio base")
    # En Perú IGV es 18%, en otros países IVA varía
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=18.00)
    
    
    # Categoría (UNIVERSAL - compartida)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )

    is_active = models.BooleanField(default=True)
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

    # ====== CAMPOS PARA SINCRONIZACIÓN CON ODOO ======

    last_sync_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Última sincronización desde Odoo"
    )

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
            models.Index(fields=['provider', 'is_active']),
            models.Index(fields=['reference']),
            models.Index(fields=['odoo_product_id']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.provider.name})"
   

    def save(self, *args, **kwargs):
        if not self.slug:
            # Slug único: nombre-proveedor
            base_slug = slugify(self.name)
            self.slug = f"{base_slug}-{self.provider.slug}"
        super().save(*args, **kwargs)

    @property
    def total_stock(self):
        return (
            self.stock_items
            .aggregate(total=Sum('quantity'))
            .get('total') or 0
        )

    @property
    def is_synced(self):
        """Producto está sincronizado con Odoo"""
        return self.odoo_product_id is not None
    
    @property
    def disponible(self):
        """Producto tiene stock disponible"""
        return self.is_active and self.total_stock > 0


class CompatibilidadProducto(models.Model):
    producto = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='compatibilidades'
    )
    variante = models.ForeignKey(
        'vehicles.VariantVehiculo',
        on_delete=models.CASCADE
    )
    
    # Campo extra que te agradecerán en el futuro:
    notas_instalacion = models.CharField(
        max_length=255, 
        blank=True, 
        help_text="Ej: Solo aplica a frenos delanteros"
    )

    class Meta:
        db_table = 'products_compatibilidad'
        verbose_name = 'Compatibilidad Producto-Vehículo'
        verbose_name_plural = 'Compatibilidades Producto-Vehículo'
        unique_together = ('producto', 'variante')
        indexes = [
            models.Index(fields=['variante', 'producto']),
        ]    



"""Gestión de Almacenes y Stock - Critical para Marketplace Multiproveedor"""


class Warehouse(models.Model):
    """
    Almacén de un proveedor específico.
    Representa ubicaciones físicas donde se almacenan productos.
    """
    provider = models.ForeignKey(
        'marketplace.Provider',
        on_delete=models.CASCADE,
        related_name='warehouses',
        verbose_name='Proveedor'
    )

    name = models.CharField(max_length=100, verbose_name='Nombre')
    city = models.CharField(max_length=100, blank=True, verbose_name='Ciudad')
    address = models.CharField(max_length=255, blank=True, verbose_name='Dirección')

    # Vínculo Odoo
    odoo_warehouse_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="ID del warehouse en Odoo"
    )

    is_active = models.BooleanField(default=True, verbose_name='Activo')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products_warehouse'
        verbose_name = 'Almacén'
        verbose_name_plural = 'Almacenes'
        unique_together = [('provider', 'name')]
        indexes = [
            models.Index(fields=['provider', 'is_active']),
            models.Index(fields=['provider']),
        ]
        ordering = ['provider', 'name']

    def __str__(self):
        return f"{self.provider.name} - {self.name}"

    @property
    def total_stock(self):
        """Stock total en este almacén"""
        return self.stock_items.aggregate(total=Sum('quantity')).get('total') or 0


class StockItem(models.Model):
    """
    Cantidad de un producto en un almacén específico.
    Es el registro REAL del stock disponible por ubicación.
    """
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='stock_items',
        verbose_name='Producto'
    )
    
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='stock_items',
        verbose_name='Almacén'
    )

    quantity = models.IntegerField(
        default=0,
        verbose_name='Cantidad',
        help_text='Cantidad disponible en el almacén'
    )
    
    # Para auditoría y control
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products_stockitem'
        verbose_name = 'Stock de Producto'
        verbose_name_plural = 'Stocks de Productos'
        unique_together = [('product', 'warehouse')]
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['warehouse']),
            models.Index(fields=['product', 'warehouse']),
            models.Index(fields=['warehouse', 'quantity']),
        ]
        ordering = ['warehouse', 'product']

    def __str__(self):
        return f"{self.product.name} - {self.warehouse.name}: {self.quantity} uds"

    @property
    def is_low_stock(self):
        """Indicador simple: stock bajo (< 5)"""
        return self.quantity < 5

    @property
    def is_out_of_stock(self):
        """Sin stock"""
        return self.quantity == 0
