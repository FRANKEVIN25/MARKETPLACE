"""
Utilidades para Multi-Tenancy en Admin
Funciones reutilizables para filtrar datos por proveedor
"""
from django.contrib.admin import SimpleListFilter
from .models import Member, Provider


def get_provider_from_request(request):
    """
    Obtiene el proveedor del usuario actual basándose en su membresía
    
    Returns:
        Provider: El proveedor asociado al usuario, o None si es superuser
    """
    if request.user.is_superuser:
        return None
    
    try:
        return Member.objects.select_related('provider').get(user=request.user).provider
    except Member.DoesNotExist:
        return None


def filter_queryset_by_provider(queryset, request, provider_field='provider'):
    """
    Filtra un queryset por el proveedor del usuario actual
    
    Args:
        queryset: QuerySet a filtrar
        request: HttpRequest del admin
        provider_field: Nombre del campo ForeignKey a Provider
    
    Returns:
        QuerySet filtrado
    """
    if request.user.is_superuser:
        return queryset
    
    provider = get_provider_from_request(request)
    if provider:
        filter_kwargs = {provider_field: provider}
        return queryset.filter(**filter_kwargs)
    
    return queryset.none()


class ProviderFilter(SimpleListFilter):
    """
    Filtro personalizado que solo muestra el proveedor del usuario actual
    Útil para no mostrar el filtro de provider a usuarios staff
    """
    title = 'Proveedor'
    parameter_name = 'provider'
    
    def lookups(self, request, model_admin):
        if request.user.is_superuser:
            return [(p.id, p.name) for p in Provider.objects.all()]
        
        provider = get_provider_from_request(request)
        if provider:
            return [(provider.id, provider.name)]
        return []
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(provider__id=self.value())
        return queryset
