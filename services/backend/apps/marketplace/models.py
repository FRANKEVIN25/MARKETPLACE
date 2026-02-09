"""
Modelos de Multi-Tenancy: Provider y Membership
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.core.exceptions import ValidationError


class Provider(models.Model):
    # Identificación
    name = models.CharField(
    max_length=100,
    unique=True,
    help_text="Nombre del proveedor (Ej: AutoPartes ABC SAC)")

    slug = models.SlugField(
    max_length=150,
    unique=True,
    blank=True,
    help_text="URL-friendly identifier")

    # Datos de negocio
    ruc = models.CharField(max_length=20, unique=True, blank=True, null=True, help_text="RUC del proveedor (Perú)")
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    # Relación con Odoo
    odoo_company_id = models.IntegerField(null=True, blank=True, unique=True, help_text="ID de la compañía en Odoo")

    # Gestión
    owner = models.ForeignKey(
    User,
    on_delete=models.PROTECT,
    related_name='owned_providers',
    help_text="Usuario dueño del proveedor")

    # Estado
    is_active = models.BooleanField(default=True)
    is_approved = models.BooleanField(
    default=False,  
    help_text="Aprobado por SuperAdmin para operar en el marketplace")

    # marcas autorizadas para este proveedor
    marcas = models.ManyToManyField(
            'vehicles.Marca',
            through='ProviderMarca', 
            related_name='proveedores'
        )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'marketplace_provider'
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        ordering = ['-created_at']

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            super().save(*args, **kwargs)

    def get_members_count(self):
        """Cantidad de usuarios en este proveedor"""
        return self.members.count()
    
    def get_products_count(self):
        """Cantidad de productos de este proveedor"""
        return self.products.count()
    
class Member(models.Model):
    """
    Membresía de usuario en un grupo.Define rol y permisos dentro del grupo.
    """
    ROLE_CHOICES = [
    ('admin', 'Administrador'),
    ('manager', 'Gerente'),
    ('staff', 'Staff'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='provider_memberships')

    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name='members')

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')

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


