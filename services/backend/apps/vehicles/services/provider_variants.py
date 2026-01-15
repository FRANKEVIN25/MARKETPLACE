# apps/vehicles/services/provider_variants.py

from apps.vehicles.models import VariantVehiculo
from apps.marketplace.models import ProviderMarca, ProviderVariantRestriccion

def variantes_disponibles_para_proveedor(provider):
    """
    Regla:
    1. Solo variantes cuya MARCA esté autorizada al proveedor
    2. Excluir variantes explícitamente restringidas
    """

    # 1. Marcas autorizadas
    marcas_ids = provider.marcas.filter(
        providermarca__activo=True
    ).values_list('id', flat=True)

    qs = VariantVehiculo.objects.filter(
        modelo__marca_id__in=marcas_ids
    )

    # 2. Excluir variantes restringidas explícitamente
    variantes_bloqueadas = ProviderVariantRestriccion.objects.filter(
        provider=provider
    ).values_list('variante_id', flat=True)

    return qs.exclude(id__in=variantes_bloqueadas)