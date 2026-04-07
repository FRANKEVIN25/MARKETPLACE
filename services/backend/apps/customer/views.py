"""
Views de Customer
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Customer, Address
from .serializers import CustomerSerializer, AddressSerializer, CustomerRegisterSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar clientes
    """
    queryset = Customer.objects.select_related(
        'user',
        'selected_vehicle_marca',
        'selected_vehicle_modelo__marca',
        'selected_vehicle_variante__modelo__marca',
        'selected_vehicle_variante__motor',
        'selected_vehicle_variante__transmision',
        'selected_vehicle_variante__traccion',
    )
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Customer.objects.all()
        return Customer.objects.filter(user=user)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny], authentication_classes=[])
    def register(self, request):
        """Registro público de cliente (individual o empresa)"""
        serializer = CustomerRegisterSerializer(data=request.data)
        if serializer.is_valid():
            customer = serializer.save()
            # Generar tokens JWT automáticamente para evitar segundo login
            refresh = RefreshToken.for_user(customer.user)
            return Response({
                'customer': CustomerSerializer(customer).data,
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get', 'patch', 'put'])
    def me(self, request):
        """Obtener o actualizar perfil del usuario actual"""
        try:
            customer = self.get_queryset().get(user=request.user)
        except Customer.DoesNotExist:
            return Response(
                {'detail': 'No tienes un perfil de cliente'},
                status=404
            )

        if request.method == 'GET':
            serializer = self.get_serializer(customer)
            return Response(serializer.data)

        # PATCH o PUT
        partial = request.method == 'PATCH'
        serializer = self.get_serializer(customer, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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