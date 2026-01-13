"""
Modelos de Clientes para Marketplace Multi-Proveedor
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from shortuuid.django_fields import ShortUUIDField


class Customer(models.Model):
    """
    Cliente que compra en el marketplace.
    Puede ser individual o empresa.
    """
    CUSTOMER_TYPE_CHOICES = [
        ('individual', 'Cliente Individual'),
        ('company', 'Empresa'),
    ]
    
    DOCUMENT_TYPE_CHOICES = [
        ('DNI', 'DNI'),
        ('RUC', 'RUC'),
        ('CE', 'Carnet de Extranjería'),
        ('PASSPORT', 'Pasaporte'),
    ]
    
    # Relación con User, para mayor flexibilidad usear AbstractUser en el futuro(version de lanzamiento).
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='customer_profile',
        help_text="Usuario asociado al cliente"
    )
    
    # Identificación
    customer_id = ShortUUIDField(
        unique=True,
        length=10,
        prefix="CUST",
        max_length=20,
        alphabet="ABCDEFGH0123456789"
    )
    
    customer_type = models.CharField(
        max_length=20,
        choices=CUSTOMER_TYPE_CHOICES,
        default='individual',
        verbose_name="Tipo de Cliente"
    )
    
    # Datos básicos
    phone = models.CharField(max_length=15, blank=True, verbose_name="Teléfono")
    
    # Documentos de identidad
    document_type = models.CharField(
        max_length=10,
        choices=DOCUMENT_TYPE_CHOICES,
        default='DNI',
        verbose_name="Tipo de Documento"
    )
    document_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Número de Documento"
    )
    
    # Para empresas
    company_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Razón Social",
        help_text="Solo para tipo empresa"
    )
    business_activity = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Actividad Económica"
    )
    
    # Preferencias
    receive_newsletter = models.BooleanField(
        default=True,
        verbose_name="Recibir Newsletter"
    )
    receive_promotions = models.BooleanField(
        default=True,
        verbose_name="Recibir Promociones"
    )
    
    # Estado y control
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Email Verificado"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_order_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha Último Pedido"
    )
    
    class Meta:
        db_table = 'customer_customer'
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['document_number']),
            models.Index(fields=['customer_type']),
            models.Index(fields=['is_active', 'is_verified']),
        ]
    
    def __str__(self):
        if self.customer_type == 'company' and self.company_name:
            return f"{self.company_name} ({self.customer_id})"
        return f"{self.user.get_full_name() or self.user.username} ({self.customer_id})"
    
    def get_full_name(self):
        """Retorna nombre completo según tipo"""
        if self.customer_type == 'company':
            return self.company_name
        return self.user.get_full_name() or self.user.username
    
    @property
    def full_document(self):
        """Retorna documento formateado"""
        return f"{self.document_type}: {self.document_number}" if self.document_number else "Sin documento"


class Address(models.Model):
    """
    Direcciones de clientes (facturación, envío, etc.)
    """
    ADDRESS_TYPE_CHOICES = [
        ('shipping', 'Dirección de Envío'),
        ('agency', 'Agencia de Transporte'),
        ('business', 'Dirección del Negocio'),
    ]
    
    # Relación
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='addresses',
        verbose_name="Cliente"
    )
    
    # Identificación
    address_id = ShortUUIDField(
        unique=True,
        length=10,
        prefix="ADDR",
        max_length=20
    )
    
    address_type = models.CharField(
        max_length=20,
        choices=ADDRESS_TYPE_CHOICES,
        default='shipping',
        verbose_name="Tipo de Dirección"
    )
    
    # Datos de contacto
    contact_name = models.CharField(max_length=100, verbose_name="Nombre de Contacto")
    contact_phone = models.CharField(max_length=15, verbose_name="Teléfono de Contacto")
    
    # Dirección completa
    street = models.CharField(max_length=200, verbose_name="Calle/Avenida")
    street_number = models.CharField(max_length=20, blank=True, verbose_name="Número")
    apartment = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Departamento/Oficina"
    )
    district = models.CharField(max_length=100, verbose_name="Distrito")
    city = models.CharField(max_length=100, verbose_name="Provincia/Ciudad")
    state = models.CharField(max_length=100, verbose_name="Departamento/Región")
    postal_code = models.CharField(max_length=20, blank=True, verbose_name="Código Postal")
    country = models.CharField(max_length=100, default="Perú", verbose_name="País")
    
    # Para agencias de transporte
    agency_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Nombre de la Agencia"
    )
    
    # Configuración
    is_default = models.BooleanField(
        default=False,
        verbose_name="Dirección Predeterminada"
    )
    reference = models.TextField(blank=True, verbose_name="Referencia")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'customer_address'
        verbose_name = 'Dirección'
        verbose_name_plural = 'Direcciones'
        ordering = ['-is_default', '-created_at']
        indexes = [
            models.Index(fields=['customer', 'is_default']),
        ]
    
    def __str__(self):
        return f"{self.get_address_type_display()} - {self.contact_name}"
    
    def get_full_address(self):
        """Retorna dirección formateada"""
        if self.address_type == 'agency':
            parts = [
                f"Agencia: {self.agency_name}" if self.agency_name else "Agencia",
                self.street,
                self.district,
                self.city,
                self.state
            ]
        else:
            parts = [
                self.street,
                f"#{self.street_number}" if self.street_number else None,
                f"{self.apartment}" if self.apartment else None,
                self.district,
                self.city,
                self.state,
                self.postal_code,
                self.country
            ]
        return ", ".join(filter(None, parts))
    
    @property
    def is_agency(self):
        return self.address_type == 'agency'


class CustomerStats(models.Model):
    """
    Estadísticas y datos adicionales del cliente
    """
    customer = models.OneToOneField(
        Customer,
        on_delete=models.CASCADE,
        related_name='stats',
        verbose_name="Cliente"
    )
    
    # Estadísticas de compra
    total_orders = models.PositiveIntegerField(
        default=0,
        verbose_name="Total de Pedidos"
    )
    total_spent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Total Gastado"
    )
    average_order_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Valor Promedio de Pedido"
    ) 
    
    # Información adicional
    preferred_brands = models.TextField(
        blank=True,
        verbose_name="Marcas Preferidas",
        help_text="Marcas/modelos de vehículos preferidos"
    )
    notes = models.TextField(blank=True, verbose_name="Notas Internas")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'customer_stats'
        verbose_name = 'Estadísticas de Cliente'
        verbose_name_plural = 'Estadísticas de Clientes'
    
    def __str__(self):
        return f"Stats - {self.customer}"
