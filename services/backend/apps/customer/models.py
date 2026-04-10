"""
Modelos de Clientes para Marketplace Multi-Proveedor
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from shortuuid.django_fields import ShortUUIDField

User = get_user_model()


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

    BUSINESS_ACTIVITY_CHOICES = [
        ('workshop', 'Taller mecánico'),
        ('parts_supplier', 'Proveedor de autopartes'),
        ('retail_store', 'Tienda de repuestos'),
        ('distributor', 'Distribuidor'),
        ('fleet', 'Flota o transporte'),
        ('dealer', 'Concesionario'),
        ('manufacturer', 'Fabricación o rectificación'),
        ('insurance', 'Aseguradora o peritaje'),
        ('other', 'Otro rubro automotriz'),
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
        max_length=40,
        blank=True,
        choices=BUSINESS_ACTIVITY_CHOICES,
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
        constraints = [
            # DNI/RUC deben ser únicos por tipo cuando están presentes.
            # La condición excluye registros sin documento (blank=True).
            models.UniqueConstraint(
                fields=['document_type', 'document_number'],
                condition=models.Q(document_number__gt=''),
                name='unique_document_if_present',
            ),
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

    @property
    def is_workshop(self):
        """Indica si la empresa opera como taller."""
        return self.customer_type == 'company' and self.business_activity == 'workshop'

    @property
    def has_selected_vehicle(self):
        return self.vehicles.filter(is_active=True).exists()


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
        constraints = [
            # Garantiza que cada cliente tenga como máximo una dirección predeterminada.
            models.UniqueConstraint(
                fields=['customer'],
                condition=models.Q(is_default=True),
                name='unique_default_address_per_customer',
            ),
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


class CustomerVehicle(models.Model):
    """
    Vehículo guardado por el cliente.
    Un cliente puede tener varios vehículos pero solo uno activo a la vez.
    El vehículo activo se usa como filtro de compatibilidad en el catálogo.
    """
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='vehicles',
        verbose_name='Cliente',
    )
    variante = models.ForeignKey(
        'vehicles.VariantVehiculo',
        on_delete=models.CASCADE,
        related_name='saved_by_customers',
        verbose_name='Variante de vehículo',
    )
    is_active = models.BooleanField(
        default=False,
        verbose_name='Activo',
        help_text='Es el vehículo actualmente seleccionado para filtrar productos.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'customer_vehicle'
        verbose_name = 'Vehículo guardado'
        verbose_name_plural = 'Vehículos guardados'
        ordering = ['-is_active', '-created_at']
        indexes = [
            models.Index(fields=['customer', 'is_active']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['customer'],
                condition=models.Q(is_active=True),
                name='unique_active_vehicle_per_customer',
            ),
        ]

    def __str__(self):
        return f"{self.customer} — {self.variante} ({'activo' if self.is_active else 'guardado'})"

    MAX_VEHICLES = 12

    @classmethod
    def set_active(cls, customer, variante):
        """
        Activa la variante indicada para el cliente.
        Si ya existe un CustomerVehicle para esa variante lo reutiliza;
        de lo contrario crea uno nuevo (respetando el límite MAX_VEHICLES).
        Siempre desactiva los demás. Retorna el CustomerVehicle activo resultante.
        """
        from django.core.exceptions import ValidationError
        from django.db import transaction
        with transaction.atomic():
            existing = cls.objects.filter(customer=customer, variante=variante).first()
            if existing is None:
                count = cls.objects.filter(customer=customer).count()
                if count >= cls.MAX_VEHICLES:
                    raise ValidationError(
                        f"No puedes guardar más de {cls.MAX_VEHICLES} vehículos. "
                        "Elimina uno antes de agregar otro."
                    )
            cls.objects.filter(customer=customer, is_active=True).update(is_active=False)
            obj, _ = cls.objects.get_or_create(customer=customer, variante=variante)
            if not obj.is_active:
                obj.is_active = True
                obj.save(update_fields=['is_active'])
        return obj

    @classmethod
    def clear_active(cls, customer):
        """Desactiva todos los vehículos del cliente (sin selección)."""
        cls.objects.filter(customer=customer, is_active=True).update(is_active=False)


class CustomerProviderStats(models.Model):
    """
    Historial de compra agregado por par (cliente, proveedor).

    Se actualiza automáticamente via signal cada vez que una SubOrder
    alcanza un estado válido: confirmado / enviado / entregado.

    Campos calculados que se cachean:
      - total_spent:             suma de SubOrder.total en estados válidos
      - total_orders:            cantidad de SubOrders válidas
      - weighted_history:        historial ponderado (usado por el motor de descuentos)
      - current_discount_percent: % de descuento activo según DiscountRule
      - next_tier_amount:        monto que falta para el siguiente tier (0 = en el máximo)
    """

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='provider_stats',
        verbose_name="Cliente",
    )
    provider = models.ForeignKey(
        'marketplace.Provider',
        on_delete=models.CASCADE,
        related_name='customer_stats',
        verbose_name="Proveedor",
    )

    # Acumulados en estados válidos (confirmado/enviado/entregado)
    total_spent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Total Gastado",
    )
    total_orders = models.PositiveIntegerField(
        default=0,
        verbose_name="Pedidos Completados",
    )

    # Caché del historial ponderado (resultado de _historial_ponderado)
    weighted_history = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Historial Ponderado",
        help_text="Valor calculado por el motor de descuentos (ventana temporal ponderada).",
    )

    # Tier de descuento actual
    current_discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="Descuento Actual (%)",
    )
    next_tier_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Falta para Siguiente Tier",
        help_text="Monto adicional necesario para el siguiente nivel de descuento (0 = tier máximo).",
    )

    last_recalculated = models.DateTimeField(
        auto_now=True,
        verbose_name="Último Recálculo",
    )

    class Meta:
        db_table = 'customer_provider_stats'
        verbose_name = 'Historial por Proveedor'
        verbose_name_plural = 'Historial por Proveedor'
        unique_together = [('customer', 'provider')]
        ordering = ['-total_spent']

    def __str__(self):
        return (
            f"{self.customer} → {self.provider.name} | "
            f"S/ {self.total_spent} | {self.current_discount_percent}%"
        )


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
    preferred_models = models.ManyToManyField(
        'vehicles.ModeloVehiculo',
        blank=True,
        related_name='preferred_by_customers',
        verbose_name='Modelos de vehículo preferidos',
        help_text='Modelos de vehículos con los que el cliente trabaja habitualmente.',
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
