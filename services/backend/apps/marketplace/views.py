"""
Views de Marketplace
Incluye endpoint de registro automático de vendors
"""
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth.models import User
from django.db import transaction
from apps.sync.tasks import create_provider_with_odoo_setup
from .models import Provider, Member
from .serializers import (
    ProviderSerializer,
    ProviderDetailSerializer,
    MembershipSerializer,
    VendorRegistrationSerializer
)
import logging

logger = logging.getLogger(__name__)


# ====== ENDPOINT DE REGISTRO DE VENDOR ======

@api_view(['POST'])
@permission_classes([AllowAny])  # Permitir registro público
def register_vendor(request):
    """
    Endpoint público para registro de vendors
    
    POST /api/marketplace/register-vendor/
    
    Body:
    {
        "username": "autopartes_abc",
        "email": "contacto@autopartesabc.com",
        "password": "SecurePass123",
        "password_confirm": "SecurePass123",
        "business_name": "AutoPartes ABC SAC",
        "business_email": "ventas@autopartesabc.com",  // opcional
        "phone": "+51 999 888 777",  // opcional
        "ruc": "20123456789",  // opcional
        "odoo_password": "OdooPass123",
        "odoo_password_confirm": "OdooPass123",
        "tier": "starter",  // opcional, default: starter
        "accept_terms": true
    }
    
    Returns:
    {
        "success": true,
        "message": "Registro exitoso. Pendiente de aprobación.",
        "user_id": 1,
        "provider_id": 1,
        "task_id": "abc-123-def"
    }
    """
    serializer = VendorRegistrationSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    validated_data = serializer.validated_data
    
    try:
        with transaction.atomic():
            # 1. Crear usuario Django
            user = User.objects.create_user(
                username=validated_data['username'],
                email=validated_data['email'],
                password=validated_data['password']
            )
            
            logger.info(f"✅ Usuario Django creado: {user.username} (ID: {user.id})")
            
            # 2. Preparar datos del provider
            provider_data = {
                'name': validated_data['business_name'],
                'email': validated_data['business_email'],
                'phone': validated_data.get('phone', ''),
                'ruc': validated_data.get('ruc', ''),
                'tier': validated_data.get('tier', 'starter')
            }
            
            # 3. Lanzar tarea asíncrona para crear Provider + Odoo setup
            task = create_provider_with_odoo_setup.delay(
                user_id=user.id,
                provider_data=provider_data,
                odoo_password=validated_data['odoo_password']
            )
            
            logger.info(f"✅ Tarea de setup lanzada: {task.id}")
            
            return Response({
                'success': True,
                'message': (
                    f'Registro exitoso para {validated_data["business_name"]}. '
                    'Tu cuenta está siendo configurada y será revisada por nuestro equipo. '
                    'Recibirás un email cuando esté aprobada.'
                ),
                'user_id': user.id,
                'username': user.username,
                'task_id': task.id,
                'business_name': validated_data['business_name']
            }, status=status.HTTP_201_CREATED)
            
    except Exception as e:
        logger.exception(f"❌ Error en registro de vendor: {e}")
        return Response({
            'success': False,
            'error': 'Error interno del servidor. Por favor intente nuevamente.',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_registration_status(request, task_id):
    """
    Verifica el estado de la tarea de registro
    
    GET /api/marketplace/registration-status/<task_id>/
    
    Returns el estado de la tarea Celery
    """
    from celery.result import AsyncResult
    
    task = AsyncResult(task_id)
    
    response_data = {
        'task_id': task_id,
        'status': task.state,
        'ready': task.ready()
    }
    
    if task.ready():
        if task.successful():
            response_data['result'] = task.result
        else:
            response_data['error'] = str(task.info)
    
    return Response(response_data)


# ====== VIEWSET DE PROVIDERS ======

class ProviderViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de Providers
    Solo accesible para usuarios autenticados
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Usuarios solo pueden ver sus propios providers
        Superadmins pueden ver todos
        """
        user = self.request.user
        
        if user.is_superuser:
            return Provider.objects.all()
        else:
            # Ver providers donde es owner o member
            return Provider.objects.filter(
                models.Q(owner=user) | models.Q(members__user=user)
            ).distinct()
    
    def get_serializer_class(self):
        """Usar serializer detallado para retrieve"""
        if self.action == 'retrieve':
            return ProviderDetailSerializer
        return ProviderSerializer
    
    @action(detail=True, methods=['post'])
    def sync_products(self, request, pk=None):
        """
        Endpoint para sincronizar productos manualmente
        POST /api/marketplace/providers/{id}/sync_products/
        """
        provider = self.get_object()
        
        if not provider.is_approved:
            return Response({
                'error': 'Provider no está aprobado'
            }, status=status.HTTP_403_FORBIDDEN)
        
        from apps.sync.tasks import sync_provider_products
        task = sync_provider_products.delay(provider.id)
        
        return Response({
            'message': 'Sincronización iniciada',
            'task_id': task.id
        })
    
    @action(detail=True, methods=['get'])
    def verify_connection(self, request, pk=None):
        """
        Verifica la conexión con Odoo
        GET /api/marketplace/providers/{id}/verify_connection/
        """
        provider = self.get_object()
        
        from apps.sync.tasks import verify_provider_odoo_connection
        result = verify_provider_odoo_connection(provider.id)
        
        return Response(result)


# ====== VIEWSET DE MEMBERS ======

class MemberViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de Members
    """
    queryset = Member.objects.all()
    serializer_class = MembershipSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtrar por provider si se proporciona"""
        queryset = super().get_queryset()
        provider_id = self.request.query_params.get('provider')
        
        if provider_id:
            queryset = queryset.filter(provider_id=provider_id)
        
        return queryset