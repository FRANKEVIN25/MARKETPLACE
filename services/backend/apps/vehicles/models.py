
# services/backend/apps/vehicles/model.py
from django.db import models
from django.utils.text import slugify

class Marca(models.Model):
    nombre = models.CharField(max_length= 100)
    slug = models.SlugField(unique=True, blank=True)
    activo = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs) 

    class Meta:
        indexes = [
            models.Index(fields=['activo']),
        ]

    def __str__(self):
        return self.nombre
    
class ModeloVehiculo(models.Model):
    nombre = models.CharField(max_length = 100)
    marca = models.ForeignKey(Marca, on_delete=models.CASCADE)
    slug = models.SlugField(unique=True, blank=True)
    activo = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.marca.nombre}-{self.nombre}")
        super().save(*args, **kwargs) 

    class Meta:
        unique_together = ('marca', 'nombre')
        indexes = [
            models.Index(fields=['marca', 'activo']),
        ]

    def __str__(self):
        return f"{self.marca.nombre} {self.nombre}"


class Transmision(models.Model):
    MT = 'MT'
    AT = 'AT'
    CVT = 'CVT'
    DCT = 'DCT'
    RED = 'RED'
    NA = 'NA'

    TIPO_CHOICES = [
        (MT, 'Manual'),
        (AT, 'Automática'),
        (CVT, 'CVT'),
        (DCT, 'DCT'),
        (RED, 'Reducción fija (EV)'),
        (NA, 'No aplica'),
    ]

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    velocidades = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('tipo', 'velocidades')

    def __str__(self):
        return f"{self.get_tipo_display()} {self.velocidades or ''}".strip()


class Traccion(models.Model):
    T4x2 = '4x2'
    T4x4 = '4x4'
    AWD = 'AWD'

    TIPO_CHOICES = [
        (T4x2, '4x2'),
        (T4x4, '4x4'),
        (AWD, 'AWD'),
    ]

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, unique=True)

    class Meta:
        indexes = [
            models.Index(fields=['tipo']),
        ]

    def __str__(self):
        return self.tipo


class Motor(models.Model):

    GSL = 'GSL'
    Hib = 'Hib'
    Ele = 'Ele'
    Dis = 'Dis'

    FUEL_CHOICES = [
        (GSL, 'GSL'),
        (Hib, 'Híbrido'),
        (Ele, 'Eléctrico'),
        (Dis, 'Diésel'),
    ]

    combustible = models.CharField(max_length=10, null=True, blank=True, choices=FUEL_CHOICES)
    cilindrada_cc = models.PositiveIntegerField(blank=True, null=True)
    codigo_motor = models.CharField(max_length=100, blank=True, null=True)
    #potencia_kw = models.PositiveIntegerField(null=True,blank=True, help_text="útil para EV / híbridos")
    tecnologia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="VVT-i, TSI, Turbo, DVVT, etc."
    )

    class Meta:
        unique_together = ('combustible','cilindrada_cc','codigo_motor','tecnologia')
        indexes = [
        models.Index(fields=['combustible']),
        models.Index(fields=['cilindrada_cc']),
        models.Index(fields=['codigo_motor']),
        ]

    def __str__(self):
        partes = []
        
        # 1. Solo calcular litros si hay cilindrada
        if self.cilindrada_cc is not None and self.cilindrada_cc > 0:
            litros = self.cilindrada_cc / 1000
            partes.append(f"{litros:.1f}L")
        elif self.combustible == 'Ele':
            partes.append("Eléctrico")
        
        # 2. Agregar código de motor si existe
        if self.codigo_motor:
            partes.append(f"({self.codigo_motor})")
            
        # 3. Agregar tecnología si existe
        if self.tecnologia:
            partes.append(self.tecnologia)
            
        # Si no hay nada, devolvemos un string genérico
        return " ".join(partes) if partes else f"Motor {self.id}"


class VariantVehiculo(models.Model):
    modelo = models.ForeignKey(ModeloVehiculo, on_delete=models.CASCADE)
    motor = models.ForeignKey(Motor, on_delete=models.PROTECT)
    transmision = models.ForeignKey(Transmision, on_delete=models.PROTECT)
    traccion = models.ForeignKey(Traccion, on_delete=models.PROTECT)

    anio_desde = models.PositiveIntegerField()
    anio_hasta = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('modelo','motor','transmision','traccion','anio_desde','anio_hasta')
        indexes = [
        models.Index(fields=['modelo', 'anio_desde', 'anio_hasta']),
        models.Index(fields=['motor']),
        models.Index(fields=['transmision']),
        models.Index(fields=['traccion']),
        ]

    def __str__(self):
        hasta = self.anio_hasta or '…'
        return (
            f"{self.modelo} | {self.motor} | "
            f"{self.transmision} | {self.traccion} "
            f"({self.anio_desde}-{hasta})"
        )


