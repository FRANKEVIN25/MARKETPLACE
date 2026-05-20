"""
Serializers de Customer
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.vehicles.models import VariantVehiculo
from .models import Customer, Address, CustomerStats, CustomerVehicle

User = get_user_model()


class CustomerSerializer(serializers.ModelSerializer):
    """Serializer para Customer"""
    email = serializers.EmailField(source='user.email', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    full_document = serializers.CharField(read_only=True)
    business_activity_display = serializers.CharField(
        source='get_business_activity_display',
        read_only=True
    )
    is_workshop = serializers.BooleanField(read_only=True)
    selected_vehicle_variante_id = serializers.PrimaryKeyRelatedField(
        queryset=VariantVehiculo.objects.all(),
        allow_null=True,
        required=False,
        write_only=True,
    )
    selected_vehicle = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Customer
        fields = [
            'id',
            'customer_id',
            'user',
            'username',
            'email',
            'full_name',
            'customer_type',
            'phone',
            'document_type',
            'document_number',
            'full_document',
            'company_name',
            'business_activity',
            'business_activity_display',
            'selected_vehicle_variante_id',
            'selected_vehicle',
            'receive_newsletter',
            'receive_promotions',
            'is_active',
            'is_verified',
            'is_workshop',
            'created_at',
            'updated_at',
            'last_order_date'
        ]
        read_only_fields = [
            'customer_id',
            'created_at',
            'updated_at',
            'last_order_date'
        ]

    _UNSET = object()

    def validate(self, attrs):
        return attrs

    def update(self, instance, validated_data):
        from django.core.exceptions import ValidationError as DjangoValidationError
        variante = validated_data.pop('selected_vehicle_variante_id', self._UNSET)
        instance = super().update(instance, validated_data)
        if variante is not self._UNSET:
            try:
                if variante is None:
                    CustomerVehicle.clear_active(instance)
                else:
                    CustomerVehicle.set_active(instance, variante)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({'selected_vehicle_variante_id': exc.message})
        return instance

    def get_selected_vehicle(self, obj):
        # Use prefetched vehicles cache when available (avoids extra DB query per customer).
        try:
            vehicles = obj.vehicles.all()  # hits prefetch cache if populated
            vehicle = next((v for v in vehicles if v.is_active), None)
        except Exception:
            vehicle = None
        if not vehicle:
            return None
        variante = vehicle.variante
        hasta = variante.anio_hasta or 'Actual'
        variante_display_name = (
            f"{variante.motor} | {variante.transmision} | {variante.traccion} "
            f"({variante.anio_desde}-{hasta})"
        )
        modelo = variante.modelo
        marca = modelo.marca
        return {
            'marca_id': marca.id,
            'marca_nombre': marca.nombre,
            'modelo_id': modelo.id,
            'modelo_nombre': modelo.nombre,
            'variante_id': variante.id,
            'variante_display_name': variante_display_name,
        }


class AddressSerializer(serializers.ModelSerializer):
    """Serializer para Address"""
    customer_name = serializers.CharField(
        source='customer.get_full_name',
        read_only=True
    )
    full_address = serializers.CharField(
        source='get_full_address',
        read_only=True
    )
    
    class Meta:
        model = Address
        fields = [
            'id',
            'address_id',
            'customer',
            'customer_name',
            'address_type',
            'contact_name',
            'contact_phone',
            'street',
            'street_number',
            'apartment',
            'district',
            'city',
            'state',
            'postal_code',
            'country',
            'agency_name',
            'is_default',
            'reference',
            'full_address',
            'is_agency',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'address_id',
            'customer',
            'customer_name',
            'full_address',
            'is_agency',
            'created_at',
            'updated_at'
        ]


class CustomerVehicleSerializer(serializers.ModelSerializer):
    """Serializer de lectura para CustomerVehicle (vehículo guardado)."""
    marca_id = serializers.IntegerField(source='variante.modelo.marca.id', read_only=True)
    marca_nombre = serializers.CharField(source='variante.modelo.marca.nombre', read_only=True)
    modelo_id = serializers.IntegerField(source='variante.modelo.id', read_only=True)
    modelo_nombre = serializers.CharField(source='variante.modelo.nombre', read_only=True)
    variante_display_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomerVehicle
        fields = [
            'id',
            'variante',
            'marca_id',
            'marca_nombre',
            'modelo_id',
            'modelo_nombre',
            'variante_display_name',
            'is_active',
            'created_at',
        ]
        read_only_fields = ['id', 'is_active', 'created_at']

    def get_variante_display_name(self, obj):
        v = obj.variante
        hasta = v.anio_hasta or 'Actual'
        return f"{v.motor} | {v.transmision} | {v.traccion} ({v.anio_desde}-{hasta})"


class CustomerStatsSerializer(serializers.ModelSerializer):
    """Serializer para CustomerStats"""
    preferred_models = serializers.PrimaryKeyRelatedField(
        many=True,
        read_only=True,
    )
    customer_name = serializers.CharField(
        source='customer.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = CustomerStats
        fields = [
            'id',
            'customer',
            'customer_name',
            'total_orders',
            'total_spent',
            'average_order_value',
            'preferred_models',
            'notes',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'total_orders',
            'total_spent',
            'average_order_value',
            'created_at',
            'updated_at'
        ]


class CustomerRegisterSerializer(serializers.Serializer):
    """
    Registro simplificado: tipo, documento, email y contraseña.
    """
    customer_type = serializers.ChoiceField(choices=['individual', 'company'])
    document_type = serializers.ChoiceField(choices=['DNI', 'RUC'])
    document_number = serializers.CharField(max_length=20)
    business_activity = serializers.ChoiceField(
        choices=Customer.BUSINESS_ACTIVITY_CHOICES,
        required=False,
        allow_blank=True
    )
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({'email': 'Ya existe una cuenta con este email.'})
        if data['customer_type'] == 'individual' and data['document_type'] != 'DNI':
            raise serializers.ValidationError({'document_type': 'Persona natural debe usar DNI.'})
        if data['customer_type'] == 'company' and data['document_type'] != 'RUC':
            raise serializers.ValidationError({'document_type': 'Empresa debe usar RUC.'})
        if data['customer_type'] == 'company' and not data.get('business_activity'):
            raise serializers.ValidationError({'business_activity': 'Selecciona la actividad económica de la empresa.'})
        if data['customer_type'] == 'individual':
            data['business_activity'] = ''
        return data

    def create(self, validated_data):
        email = validated_data['email']
        username = email.split('@')[0]
        # Asegurar username único
        base = username
        i = 1
        while User.objects.filter(username=username).exists():
            username = f'{base}{i}'
            i += 1
        is_individual = validated_data['customer_type'] == 'individual'
        user = User.objects.create_user(
            username=username,
            email=email,
            password=validated_data['password'],
            is_active=is_individual,
        )
        customer = Customer.objects.create(
            user=user,
            customer_type=validated_data['customer_type'],
            document_type=validated_data['document_type'],
            document_number=validated_data['document_number'],
            business_activity=validated_data.get('business_activity', ''),
        )
        return customer