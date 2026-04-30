"""
Modelos de Productos - Versión MVP
"""
import uuid

from decimal import Decimal
from django.db import models
from django.utils.text import slugify
from mptt.models import MPTTModel, TreeForeignKey
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from .managers import ProductManager
from django.db.models import Sum

class Category(MPTTModel):
    """
    Categoría jerárquica de productos.
    UNIVERSAL - No tiene provider (compartida por todos).

    Slug:
        Se genera una única vez al crear la categoría y no se actualiza
        aunque cambie el nombre. Esto garantiza URLs estables para SEO.
        Si el slug base ya existe, se añade un sufijo numérico (-1, -2…).
    """
    IMPORT_CODE_PREFIXES = {
        0: 'CAT',
        1: 'SUB',
        2: 'LEF',
    }

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
    is_active = models.BooleanField(default=True)

    # Clave estable de sincronización Django -> Odoo.
    # No depende del PK de Django, del nombre ni del ID nativo de Odoo.
    sync_key = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text="Clave estable usada para vincular la categoría con Odoo.",
    )

    import_code = models.CharField(
        max_length=16,
        unique=True,
        editable=False,
        blank=True,
        help_text=(
            "Código corto y estable para proyección de External ID en Odoo. "
            "Se genera en Django y no depende del nombre de la categoría."
        ),
    )

    # Vínculo cacheado con Odoo para resolución operativa rápida.
    # Django es maestro de categorías; la fuente de verdad del vínculo es
    # sync_key <-> product.category.django_sync_key.
    # odoo_category_id solo guarda el ID nativo actual de Odoo para evitar
    # búsquedas extra en syncs posteriores.
    odoo_category_id = models.IntegerField(
        null=True,
        blank=True,
        unique=True,
        help_text="ID de la categoría en Odoo (product.category). "
                  "Se usa como cache operativa local; la vinculación estable la define sync_key."
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class MPTTMeta:
        order_insertion_by = ['name']

    class Meta:
        db_table = 'products_category'
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['parent_id']),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        if self.pk and self.parent_id == self.pk:
            raise ValidationError("Una categoría no puede ser su propio padre.")

    def _generate_unique_slug(self):
        base_slug = slugify(self.name)
        slug = base_slug
        counter = 1
        while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    @classmethod
    def get_import_code_prefix(cls, level: int | None) -> str:
        return cls.IMPORT_CODE_PREFIXES.get(level if level is not None else 0, 'CAT')

    @classmethod
    def build_next_import_code(cls, level: int | None) -> str:
        prefix = cls.get_import_code_prefix(level)
        last_code = (
            cls.objects.filter(import_code__startswith=prefix)
            .order_by('-import_code')
            .values_list('import_code', flat=True)
            .first()
        )
        next_number = int(last_code[len(prefix):]) + 1 if last_code else 1
        return f'{prefix}{next_number:03d}'

    def _target_level_for_import_code(self) -> int:
        if self.parent_id:
            parent_level = self.parent.level if self.parent else Category.objects.only('level').get(pk=self.parent_id).level
            return parent_level + 1
        if self.pk and hasattr(self, 'level') and self.level is not None:
            return self.level
        return 0

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
        if not self.import_code:
            self.import_code = self.build_next_import_code(self._target_level_for_import_code())
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
    
    odoo_state = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pendiente'),
            ('synced', 'Sincronizado'),
            ('failed', 'Fallido')
        ],
        default='pending',
        db_index=True
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
    reference = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        db_index=True,
        help_text="SKU o referencia del proveedor. Puede estar vacía (ej: productos importados sin código)"
    )
    slug = models.SlugField(max_length=255, unique=True, blank=True, editable=False)
    
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
    odoo_image_version = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="Versión remota usada para decidir si la imagen debe refrescarse desde Odoo."
    )

    description = models.TextField(blank=True, null=True)
    
    # Precio (BASE IMPONIBLE)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Precio base",
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    # En Perú IGV es 18%, en otros países IVA varía
    tax_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=18.00,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    
    
    # Categoría (UNIVERSAL - compartida)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )

    is_active = models.BooleanField(default=True)
    is_published = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Visible públicamente en el marketplace. Un producto puede estar activo pero no publicado (ej: borrador)."
    )
    es_universal = models.BooleanField(default=False, db_index=True) # si es True no necesita compatibilidad

    SIDE_CHOICES = [
        ('left', 'Izquierda'),
        ('right', 'Derecha'),
        ('front', 'Delantera'),
        ('rear', 'Posterior'),
        ('both', 'Ambos lados'),
        ('na', 'No aplica'),
    ]

    autopart_side = models.CharField(
        max_length=10,
        choices=SIDE_CHOICES,
        verbose_name='Lado del vehículo',
        help_text='Lado del vehículo al que aplica la autoparte',
        default='na',
        blank=True
    )

    QUALITY_CHOICES = [
        ('original', 'Original'),
        ('oem', 'OEM'),
        ('aftermarket_premium', 'Alternativo Premium'),
        ('aftermarket_standard', 'Alternativo Estándar'),
    ]

    autopart_quality = models.CharField(
        max_length=20,
        choices=QUALITY_CHOICES,
        verbose_name='Calidad del repuesto',
        default='aftermarket_standard',
        blank=True
    )

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

    # ====== STOCK DENORMALIZADO ======
    # Se mantiene actualizado via signals (apps/products/signals.py).
    # Evita N+1 queries en listados de productos.
    total_stock_cached = models.IntegerField(
        default=0,
        help_text="Stock total agregado. Actualizado automáticamente por signals."
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


    # Stock mínimo para considerar el producto disponible (mitiga sobreventa).
    # Valor configurable: podría moverse a settings.py o a un campo DB en el futuro.
    MIN_STOCK_THRESHOLD = 2

    objects = ProductManager()

    class Meta:
        db_table = 'products_product'
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['-created_at']
        constraints = [
            # Referencia única por proveedor, solo cuando reference no es NULL ni vacía.
            # Permite importar productos desde Odoo sin referencia sin colisiones.
            models.UniqueConstraint(
                fields=['provider', 'reference'],
                condition=models.Q(reference__isnull=False) & ~models.Q(reference=''),
                name='unique_provider_reference_not_null'
            )
        ]
        indexes = [
            models.Index(fields=['provider', 'is_active']),
            models.Index(fields=['reference']),
            # Compuesto: el sync siempre filtra por (provider, odoo_product_id)
            models.Index(fields=['provider', 'odoo_product_id']),
            # Compatibilidades resuelven productos por (provider, odoo_template_id)
            models.Index(fields=['provider', 'odoo_template_id']),
            models.Index(fields=['slug']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.provider.name})"
   

    def generate_unique_slug(self):
        """
        Genera un slug estable y único.
        Usa provider_id (entero) en lugar de provider.slug para que el slug
        no se rompa si el proveedor cambia su slug en el futuro.
        """
        base_slug = slugify(self.name)
        slug = f"{base_slug}-{self.provider_id}"
        counter = 1
        while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{self.provider_id}-{counter}"
            counter += 1
        return slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_unique_slug()
        super().save(*args, **kwargs)

    @property
    def total_stock(self):
        """Stock total. Retorna el valor cacheado (sin query extra)."""
        return self.total_stock_cached

    @property
    def price_with_tax(self) -> float:
        """Precio final con IGV/IVA incluido. Fuente de verdad para precio al cliente."""
        return float(self.price * (1 + self.tax_percent / 100))

    def recalculate_stock(self):
        """Recalcula y persiste total_stock_cached desde Odoo qty_available.
        Usado por el comando de sync — no depende de StockItem."""

        # Suma directa: el campo es mantenido por el sync de Odoo
        # Este método queda como puerta de entrada para forzar un recalculo
        # si por alguna razón el cache se desincroniza.
        Product.objects.filter(pk=self.pk).update(total_stock_cached=self.total_stock_cached)

    @property
    def is_synced(self):
        """Producto está sincronizado con Odoo"""
        return self.odoo_product_id is not None

    @property
    def is_available(self):
        """
        Producto está disponible para compra en el marketplace.

        Nota: accede a self.provider y self.category directamente.
        En listados usar siempre select_related('provider', 'category')
        para evitar N+1 queries.
        """
        return (
            self.is_active
            and self.is_published
            and self.total_stock_cached >= self.MIN_STOCK_THRESHOLD
            and self.provider.is_active
            and (self.category.is_active if self.category_id else True)
        )


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
        constraints = [
            models.UniqueConstraint(
                fields=['producto', 'variante'],
                name='unique_producto_variante'
            )
        ]
        indexes = [
            models.Index(fields=['variante', 'producto']),
        ]    



"""
Tiendas físicas del proveedor (puntos de retiro).
NO gestiona stock — el stock se maneja como total_stock_cached en Product,
sincronizado directamente desde Odoo. Esta clase solo representa
ubicaciones físicas donde el cliente puede recoger su pedido.
"""


class Store(models.Model):
    """
    Tienda o punto de retiro de un proveedor.
    Simple: nombre, dirección y ciudad — nada más.
    El stock se consulta a nivel de provider, no por tienda.
    """
    provider = models.ForeignKey(
        'marketplace.Provider',
        on_delete=models.CASCADE,
        related_name='stores',
        verbose_name='Proveedor'
    )

    name = models.CharField(max_length=100, verbose_name='Nombre')
    city = models.CharField(max_length=100, blank=True, verbose_name='Ciudad')
    address = models.CharField(max_length=255, blank=True, verbose_name='Dirección')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Teléfono')

    is_active = models.BooleanField(default=True, verbose_name='Activo')

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products_store'
        verbose_name = 'Tienda'
        verbose_name_plural = 'Tiendas'
        unique_together = [('provider', 'name')]
        indexes = [
            models.Index(fields=['provider', 'is_active']),
        ]
        ordering = ['provider', 'name']

    def __str__(self):
        return f"{self.provider.name} — {self.name}"
