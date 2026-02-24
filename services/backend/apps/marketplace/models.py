"""
Modelos de Multi-Tenancy: Provider y Membership
ACTUALIZADO: Incluye gestión de usuarios Odoo y credenciales
"""
from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password
from django.utils.text import slugify
from django.core.exceptions import ValidationError
import secrets


class TierChoices(models.TextChoices):
    """Niveles de servicio para providers"""
    STARTER = 'starter', 'Starter (Compartido)'
    PRO = 'pro', 'Pro (Compartido Optimizado)'  
    PREMIUM = 'premium', 'Premium (Instancia Dedicada)'


class Provider(models.Model):
    # ====== IDENTIFICACIÓN ======
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Nombre del proveedor (Ej: AutoPartes ABC SAC)"
    )

    slug = models.SlugField(
        max_length=150,
        unique=True,
        blank=True,
        help_text="URL-friendly identifier"
    )

    # ====== DATOS DE NEGOCIO ======
    ruc = models.CharField(
        max_length=20, 
        unique=True, 
        blank=True, 
        null=True, 
        help_text="RUC del proveedor (Perú)"
    )
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    # ====== RELACIÓN CON ODOO ======
    odoo_company_id = models.IntegerField(
        null=True, 
        blank=True, 
        unique=True, 
        help_text="ID de la compañía en Odoo"
    )
    
    # NUEVO: Credenciales del usuario Odoo
    odoo_user_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="ID del usuario en Odoo"
    )

    odoo_username = models.EmailField(
        null=True,
        blank=True,
        unique=True,
        help_text="Email/username para login en Odoo"
    )

    odoo_password_hash = models.CharField(
        max_length=255,
        blank=True,
        help_text="Password de Odoo (encriptado con Django hasher)"
    )
    
    # ====== MULTI-TENANT CONFIGURATION ======
    
    # Tier y configuración
    tier = models.CharField(
        max_length=20,
        choices=TierChoices.choices,
        default=TierChoices.STARTER,
        help_text="Nivel de servicio del proveedor"
    )
    
    # Para SHARED instances (Starter y Pro)
    shared_instance_name = models.CharField(
        max_length=50,
        default='ecomparts-odoo-shared',
        help_text="Nombre de la instancia compartida de Odoo"
    )
    
    # Para DEDICATED instances (Premium)
    dedicated_instance_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="ID del contenedor Docker (solo Premium)"
    )
    dedicated_odoo_url = models.URLField(
        null=True,
        blank=True,
        help_text="URL de la instancia dedicada (solo Premium)"
    )
    dedicated_db_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Nombre de la BD dedicada (solo Premium)"
    )
    
    # Métricas para auto-upgrade
    monthly_orders = models.IntegerField(
        default=0,
        help_text="Órdenes procesadas este mes"
    )
    total_products = models.IntegerField(
        default=0,
        help_text="Total de productos activos"
    )
    monthly_revenue = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Facturación mensual en PEN"
    )
    
    # ====== END MULTI-TENANT CONFIGURATION ======

    # ====== GESTIÓN ======
    owner = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='owned_providers',
        help_text="Usuario dueño del proveedor"
    )

    # ====== ESTADO ======
    is_active = models.BooleanField(default=True)
    is_approved = models.BooleanField(
        default=False,  
        help_text="Aprobado por SuperAdmin para operar en el marketplace"
    )


    # ============================================
    # CONFIGURACIÓN TRIBUTARIA (Multi-tenant)
    # ============================================
    TAX_REGIME_CHOICES = [
        ('RUS', 'Régimen Único Simplificado'),
        ('RER', 'Régimen Especial de Renta'),
        ('RMT', 'Régimen MYPE Tributario'),
        ('GENERAL', 'Régimen General'),
    ]
    
    COMPROBANTE_CHOICES = [
        ('boleta', 'Solo Boleta'),
        ('factura', 'Solo Factura'),
        ('ambos', 'Boleta y Factura'),
    ]
    
    tax_regime = models.CharField(
        max_length=20,
        choices=TAX_REGIME_CHOICES,
        default='GENERAL',
        verbose_name="Régimen Tributario"
    )
    
    igv_applicable = models.BooleanField(
        default=True,
        verbose_name="Aplica IGV (18%)",
        help_text="False solo para RUS"
    )
    
    emite_comprobante = models.CharField(
        max_length=20,
        choices=COMPROBANTE_CHOICES,
        default='ambos',
        verbose_name="Tipo de Comprobante"
    )
    
    # ============================================
    # DATOS DE PAGO (Modelo Descentralizado)
    # ============================================
    banco_nombre = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Nombre del Banco"
    )
    
    banco_cuenta = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Número de Cuenta"
    )
    
    banco_cci = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="CCI Interbancario"
    )
    
    yape_numero = models.CharField(
        max_length=15,
        blank=True,
        verbose_name="Número Yape"
    )
    
    plin_numero = models.CharField(
        max_length=15,
        blank=True,
        verbose_name="Número Plin"
    )
    
    # ====== METADATA ======
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ====== LÍMITES POR TIER ======
    TIER_LIMITS = {
        'starter': {
            'max_products': 100,
            'max_orders_month': 50,
            'max_api_calls_day': 1000,
            'price': 0,  # Gratis
            'commission': 0.08,  # 8%
        },
        'pro': {
            'max_products': 1000,
            'max_orders_month': 500,
            'max_api_calls_day': 5000,
            'price': 99,  # S/ 99/mes
            'commission': 0.05,  # 5%
        },
        'premium': {
            'max_products': None,  # Ilimitado
            'max_orders_month': None,
            'max_api_calls_day': None,
            'price': 299,  # S/ 299/mes
            'commission': 0.03,  # 3%
        }
    }

    class Meta:
        db_table = 'marketplace_provider'
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tier']),
            models.Index(fields=['is_active', 'is_approved']),
            models.Index(fields=['odoo_company_id']),
            models.Index(fields=['odoo_user_id']),
            models.Index(fields=['odoo_username']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_tier_display()})"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    # ====== MÉTODOS DE GESTIÓN DE CREDENCIALES ODOO ======
    
    def set_odoo_password(self, raw_password):
        """
        Guarda el password de Odoo encriptado usando Django's password hasher
        
        Args:
            raw_password (str): Password en texto plano
        """
        if not raw_password:
            raise ValueError("El password no puede estar vacío")
        
        if len(raw_password) < 8:
            raise ValueError("El password debe tener al menos 8 caracteres")
        
        self.odoo_password_hash = make_password(raw_password)
    
    def verify_odoo_password(self, raw_password):
        """
        Verifica si el password proporcionado coincide con el guardado
        
        Args:
            raw_password (str): Password a verificar
            
        Returns:
            bool: True si el password es correcto
        """
        if not self.odoo_password_hash:
            return False
        
        return check_password(raw_password, self.odoo_password_hash)
    
    def generate_odoo_username(self):
        """
        Genera un username único para Odoo basado en el email o nombre
        
        Returns:
            str: Username único
        """
        if self.email:
            return self.email.lower()
        else:
            # Generar email único basado en el nombre
            base_username = slugify(self.name).replace('-', '_')
            return f"{base_username}@ecomparts.local"
    
    def has_odoo_credentials(self):
        """
        Verifica si el provider tiene credenciales completas de Odoo
        
        Returns:
            bool: True si tiene credenciales completas
        """
        return all([
            self.odoo_company_id,
            self.odoo_user_id,
            self.odoo_username,
            self.odoo_password_hash
        ])
    
    def get_odoo_connector(self):
        """
        Retorna un conector de Odoo configurado con las credenciales de este provider
        
        Returns:
            OdooConnector: Instancia configurada con credenciales del provider
            
        Raises:
            ValueError: Si no tiene credenciales completas
        """
        if not self.has_odoo_credentials():
            raise ValueError(
                f"Provider {self.name} no tiene credenciales completas de Odoo. "
                "Use create_odoo_setup() primero."
            )
        
        from apps.sync.odoo_connector import OdooConnector
        connection_info = self.get_odoo_connection_info()
        
        return OdooConnector(
            url=connection_info['url'],
            db_name=connection_info['db'],
            username=self.odoo_username,
            password=self.odoo_password_hash  # El connector debe manejar esto
        )

    # ====== MULTI-TENANT METHODS ======
    
    def get_tier_limits(self):
        """Retorna los límites del tier actual"""
        return self.TIER_LIMITS.get(self.tier, self.TIER_LIMITS['starter'])
    
    def check_upgrade_needed(self):
        """
        Verifica si el provider necesita upgrade automático.
        Retorna el tier sugerido o None.
        """
        limits = self.get_tier_limits()
        
        if self.tier == 'starter':
            # Upgrade a Pro si está cerca del límite (80%)
            if (self.total_products > limits['max_products'] * 0.8 or 
                self.monthly_orders > limits['max_orders_month'] * 0.8):
                return 'pro'
        
        elif self.tier == 'pro':
            # Upgrade a Premium si supera límites o tiene buen revenue
            if (self.total_products > limits['max_products'] * 0.8 or
                self.monthly_orders > limits['max_orders_month'] * 0.8 or
                self.monthly_revenue > 5000):  # 5000 PEN/mes
                return 'premium'
        
        return None
    
    def get_usage_percentage(self):
        """Retorna % de uso de recursos por categoría"""
        limits = self.get_tier_limits()
        usage = {}
        
        if limits['max_products']:
            usage['products'] = (self.total_products / limits['max_products']) * 100
        else:
            usage['products'] = 0
            
        if limits['max_orders_month']:
            usage['orders'] = (self.monthly_orders / limits['max_orders_month']) * 100
        else:
            usage['orders'] = 0
            
        return usage
    
    def is_dedicated_instance(self):
        """Verifica si tiene instancia dedicada"""
        return self.tier == 'premium' and self.dedicated_instance_id is not None
    
    def is_near_limit(self, threshold=80):
        """
        Verifica si está cerca del límite de recursos (default 80%)
        """
        usage = self.get_usage_percentage()
        return any(percentage >= threshold for percentage in usage.values())
    
    def get_odoo_connection_info(self):
        """
        Retorna la información de conexión a Odoo según el tier
        
        Returns:
            dict: Información de conexión (url, db, company_id, instance_type)
        """
        if self.is_dedicated_instance():
            return {
                'url': self.dedicated_odoo_url,
                'db': self.dedicated_db_name,
                'company_id': None,  # En instancia dedicada no usa company_id
                'instance_type': 'dedicated'
            }
        else:
            return {
                'url': 'http://ecomparts-odoo-shared:8069',
                'db': 'ecomparts_odoo_shared',
                'company_id': self.odoo_company_id,
                'instance_type': 'shared'
            }
    
    # ====== END MULTI-TENANT METHODS ======

    def get_members_count(self):
        """Cantidad de usuarios en este proveedor"""
        return self.members.count()
    
    def get_products_count(self):
        """Cantidad de productos de este proveedor"""
        return self.products.count()


class Member(models.Model):
    """
    Membresía de usuario en un grupo. Define rol y permisos dentro del grupo.
    """
    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('manager', 'Gerente'),
        ('staff', 'Staff'),
    ]

    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='provider_memberships'
    )

    provider = models.ForeignKey(
        Provider, 
        on_delete=models.CASCADE, 
        related_name='members'
    )

    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, 
        default='staff'
    )

    # Permisos granulares
    can_manage_products = models.BooleanField(default=True)
    can_manage_prices = models.BooleanField(default=False)
    can_manage_stock = models.BooleanField(default=False)
    can_invite_users = models.BooleanField(default=False)
    can_sync_odoo = models.BooleanField(default=False)
    
    # Metadata
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'marketplace_member'
        verbose_name = 'Miembro'
        verbose_name_plural = 'Miembros'
        unique_together = ['user', 'provider']
        ordering = ['-joined_at']
        indexes = [
            models.Index(fields=['user', 'provider']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.provider.name} ({self.role})"
    
    def clean(self):
        """Validaciones"""
        # Admin tiene todos los permisos
        if self.role == 'admin':
            self.can_manage_products = True
            self.can_manage_prices = True
            self.can_manage_stock = True
            self.can_invite_users = True
            self.can_sync_odoo = True

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


