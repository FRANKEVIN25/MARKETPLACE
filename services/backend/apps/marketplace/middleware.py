"""
Middleware de Multi-Tenancy
Detecta automáticamente el grupo del usuario y lo inyecta en el request.
"""
import logging
from .models import Member
logger = logging.getLogger(__name__)


class TenantScopeMiddleware:
    """
    Middleware que agrega request.current_group basado en el usuario
    autenticado.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Inicializar atributos
        request.current_provider = None
        request.current_membership = None
        # Solo para usuarios autenticados
        if request.user and request.user.is_authenticated:
            try:
                # Buscar membresía del usuario
                membership = Member.objects.select_related('provider').filter(
                user=request.user,
                provider__is_active=True
                ).first()
                if membership:
                    request.current_provider = membership.provider
                    request.current_membership = membership
                    logger.debug(
                    f"Usuario {request.user.username} → Grupo{membership.group.name}")
                else:
                    logger.debug(
                    f"Usuario {request.user.username} sin proveedor asignado"
                    )
            except Exception as e:
                logger.error(f"Error en TenantScopeMiddleware: {e}")
                
        response = self.get_response(request)
        return response