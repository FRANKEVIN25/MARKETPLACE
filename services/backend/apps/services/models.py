from django.db import models
from django.contrib.auth.models import User

"""
El valor real no está en listar talleres, está en reducir el riesgo del cliente.
los talleres también son potenciales proveedores, odoo es flexible para manejar
paralelamente o de forma independiente el modulo de vehículos y talleres
"""
class Workshop(models.Model):
    WORKSHOP_TIER_CHOICES = [
        ('L1', 'Básico / Barrio'),
        ('L2', 'Especializado'),
        ('L3', 'Integral'),
        ('L4', 'Avanzado / Flotas'),
        ('L5', 'Cadena / Concesionario'),
    ]

    PARTS_RELATION_CHOICES = [
        ('SERVICE_ONLY', 'Solo servicio'),
        ('SERVICE_AND_PARTS', 'Servicio y venta'),
        ('DISTRIBUTOR', 'Distribuidor'),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workshops')

    # 🔗 PUENTE OPCIONAL A PROVIDER (FUTURO)
    provider = models.OneToOneField(
        'marketplace.Provider',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workshop',
        help_text="Si el taller también vende como proveedor"
    )

    name = models.CharField(max_length=255)
    ruc = models.CharField(max_length=11, blank=True, null=True)

    tier = models.CharField(max_length=2, choices=WORKSHOP_TIER_CHOICES)
    parts_relation = models.CharField(max_length=20, choices=PARTS_RELATION_CHOICES)

    description = models.TextField(blank=True)
    years_experience = models.PositiveIntegerField(default=0)

    address = models.CharField(max_length=255)
    district = models.CharField(max_length=100)
    city = models.CharField(max_length=100, default='Lima')

    phone = models.CharField(max_length=20)
    whatsapp = models.CharField(max_length=20, blank=True)

    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


  # Ejemplos: Motor, Frenos , Suspensión, Electricidad, Diagnóstico

class ServiceCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
    

  # Ejemplos: Motor → Afinamiento, Frenos → Cambio de pastillas , Diagnóstico → Escaneo computarizado
class Service(models.Model):
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='services')
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    """
    # 🔗 FUTURO: producto asociado en marketplace
    product = models.OneToOneField(
        'products.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_definition',
        help_text="Producto tipo servicio asociado (si se vende)"
    )

    # 🔗 FUTURO: sincronización Odoo
    # odoo_product_id = models.IntegerField(null=True, blank=True)

    if workshop.provider:
        # Mostrar productos del proveedor
        products = workshop.provider.products.filter(active=True)

        # Mostrar servicios vendibles
        services = Product.objects.filter(
            product_type='service',
            provider=workshop.provider
        )
    """

    def __str__(self):
        return f"{self.category.name} - {self.name}"    
    

class WorkshopService(models.Model):
    workshop = models.ForeignKey(Workshop, on_delete=models.CASCADE, related_name='services')
    service = models.ForeignKey(Service, on_delete=models.CASCADE)

    is_specialized = models.BooleanField(
        default=False,
        help_text="Indica si es un servicio fuerte del taller"
    )

    def __str__(self):
        return f"{self.workshop.name} - {self.service.name}"



class WorkshopServiceHistory(models.Model):
    workshop = models.ForeignKey(Workshop, on_delete=models.CASCADE, related_name='service_history')
    service = models.ForeignKey(Service, on_delete=models.CASCADE)

    total_jobs = models.PositiveIntegerField(default=0)
    repeat_failures = models.PositiveIntegerField(default=0)

    last_service_date = models.DateField(blank=True, null=True)

    class Meta:
        unique_together = ('workshop', 'service')
