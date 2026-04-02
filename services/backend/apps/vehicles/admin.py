from django.contrib import admin
from .models import Marca, ModeloVehiculo, Transmision, Traccion, Motor, VariantVehiculo

@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre',)

@admin.register(ModeloVehiculo)
class ModeloVehiculoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'marca', 'activo')
    list_filter = ('marca', 'activo')
    search_fields = ('nombre', 'marca__nombre')

@admin.register(Transmision)
class TransmisionAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'velocidades')
    list_filter = ('tipo',)

@admin.register(Traccion)
class TraccionAdmin(admin.ModelAdmin):
    list_display = ('tipo',)

@admin.register(Motor)
class MotorAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'combustible', 'cilindrada_cc', 'codigo_motor', 'tecnologia')
    list_filter = ('combustible', 'tecnologia')
    search_fields = ('codigo_motor', 'tecnologia')

@admin.register(VariantVehiculo)
class VariantVehiculoAdmin(admin.ModelAdmin):
    # Organiza las columnas en la lista principal
    list_display = (
        'modelo',
        'get_marca',
        'motor',
        'transmision',
        'traccion',
        'anio_desde',
        'anio_hasta',
        'odoo_variante_id',
        'get_providers_count',
    )

    # Agrega filtros laterales para encontrar variantes rápido
    list_filter = (
        'modelo__marca',
        'transmision__tipo',
        'traccion__tipo',
        'anio_desde',
    )

    # Permite buscar por nombre de modelo, marca o código de motor.
    # Estos campos también son usados por el widget filter_horizontal
    # de ProviderAdmin para buscar variantes al asignar el scope.
    search_fields = (
        'modelo__nombre',
        'modelo__marca__nombre',
        'motor__codigo_motor',
        'motor__tecnologia',
        'anio_desde',
        'anio_hasta',
    )

    readonly_fields = ('odoo_variante_id',)

    @admin.display(ordering='modelo__marca', description='Marca')
    def get_marca(self, obj):
        return obj.modelo.marca

    @admin.display(description='Providers')
    def get_providers_count(self, obj):
        return obj.providers_habilitados.count()

