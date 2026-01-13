"""
Views de Customer
"""
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Customer, Address
from .serializers import CustomerSerializer, AddressSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar clientes
    """
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filtrar según usuario"""
        user = self.request.user
        
        # SuperAdmin ve todos
        if user.is_superuser:
            return Customer.objects.all()
        
        # Usuario ve solo su perfil
        return Customer.objects.filter(user=user)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Obtener perfil del usuario actual"""
        try:
            customer = Customer.objects.get(user=request.user)
            serializer = self.get_serializer(customer)
            return Response(serializer.data)
        except Customer.DoesNotExist:
            return Response(
                {'detail': 'No tienes un perfil de cliente'},
                status=404
            )


class AddressViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar direcciones
    """
    queryset = Address.objects.all()
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filtrar direcciones del usuario"""
        user = self.request.user
        
        # SuperAdmin ve todas
        if user.is_superuser:
            return Address.objects.all()
        
        # Usuario ve solo sus direcciones
        try:
            customer = Customer.objects.get(user=user)
            return Address.objects.filter(customer=customer)
        except Customer.DoesNotExist:
            return Address.objects.none()
    
    def perform_create(self, serializer):
        """Asignar automáticamente el customer del usuario"""
        customer = Customer.objects.get(user=self.request.user)
        serializer.save(customer=customer)