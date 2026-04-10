"""
Views de Customer
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Customer, Address, CustomerVehicle
from .serializers import CustomerSerializer, AddressSerializer, CustomerRegisterSerializer, CustomerVehicleSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar clientes
    """
    queryset = Customer.objects.select_related('user')
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]

    # Acciones que necesitan los datos completos del vehículo activo.
    _VEHICLE_PREFETCH_ACTIONS = frozenset({'me', 'retrieve', 'update', 'partial_update'})

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Customer.objects.select_related('user')
        qs = Customer.objects.filter(user=user).select_related('user')
        if self.action in self._VEHICLE_PREFETCH_ACTIONS:
            qs = qs.prefetch_related(
                'vehicles__variante__modelo__marca',
                'vehicles__variante__motor',
                'vehicles__variante__transmision',
                'vehicles__variante__traccion',
            )
        return qs

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
            # get_queryset() ya filtra por user; .get() sin argumentos es suficiente.
            customer = self.get_queryset().get()
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

        if user.is_superuser:
            return Address.objects.select_related('customer__user').all()

        # JOIN directo: evita la query extra Customer.objects.get(user=user).
        return Address.objects.filter(customer__user=user).select_related('customer')

    def perform_create(self, serializer):
        """Asignar automáticamente el customer del usuario"""
        # customer_profile es el related_name del OneToOne; Django cachea el resultado.
        serializer.save(customer=self.request.user.customer_profile)


class CustomerVehicleViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar los vehículos guardados del cliente.

    Endpoints:
      GET    /customer/vehicles/           → lista los vehículos del cliente
      POST   /customer/vehicles/           → guarda un nuevo vehículo
      DELETE /customer/vehicles/{id}/      → elimina un vehículo guardado
      POST   /customer/vehicles/{id}/set_active/ → lo pone como activo
    """
    serializer_class = CustomerVehicleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        try:
            customer = Customer.objects.get(user=self.request.user)
        except Customer.DoesNotExist:
            return CustomerVehicle.objects.none()
        return (
            CustomerVehicle.objects
            .filter(customer=customer)
            .select_related(
                'variante__modelo__marca',
                'variante__motor',
                'variante__transmision',
                'variante__traccion',
            )
        )

    def perform_create(self, serializer):
        # customer_profile es el related_name del OneToOne; Django cachea el resultado.
        customer = self.request.user.customer_profile
        variante = serializer.validated_data['variante']
        # Verificar límite antes de crear (solo si la variante es nueva para este cliente).
        if not CustomerVehicle.objects.filter(customer=customer, variante=variante).exists():
            count = CustomerVehicle.objects.filter(customer=customer).count()
            if count >= CustomerVehicle.MAX_VEHICLES:
                from rest_framework.exceptions import ValidationError
                raise ValidationError(
                    f"No puedes guardar más de {CustomerVehicle.MAX_VEHICLES} vehículos. "
                    "Elimina uno antes de agregar otro."
                )
        obj, _ = CustomerVehicle.objects.get_or_create(customer=customer, variante=variante)
        serializer.instance = obj

    @action(detail=True, methods=['post'])
    def set_active(self, request, pk=None):
        """Marca este vehículo como el activo (desactiva los demás)."""
        vehicle = self.get_object()
        CustomerVehicle.set_active(vehicle.customer, vehicle.variante)
        vehicle.refresh_from_db()
        return Response(self.get_serializer(vehicle).data)