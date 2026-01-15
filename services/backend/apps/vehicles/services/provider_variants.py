# apps/vehicles/services/provider_variants.py

from apps.vehicles.models import VariantVehiculo
from apps.marketplace.models import ProviderMarca, ProviderVariantRestriccion
from django.db.models import Q
def variantes_disponibles_para_proveedor(provider):
    """
    Regla:
    1. Solo variantes cuya MARCA esté autorizada al proveedor
    2. Excluir variantes explícitamente restringidas
    """
    if not provider:
        return VariantVehiculo.objects.none()
    # 1. Marcas autorizadas
    marcas_ids = provider.marcas.filter(
        proveedores_autorizados__activo=True  # <- Corregido
    ).values_list('id', flat=True)

    # Variantes de modelos de marcas autorizadas
    variantes_autorizadas = VariantVehiculo.objects.filter(
        modelo__marca_id__in=marcas_ids
    )
    
    # Excluir variantes específicamente restringidas
    variantes_restringidas_ids = provider.variantes_restringidas.values_list(
        'variante_id', flat=True
    )

    return variantes_autorizadas.exclude(id__in=variantes_restringidas_ids)