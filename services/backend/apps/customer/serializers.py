"""
Serializers de Customer
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from apps.vehicles.models import Marca, ModeloVehiculo, VariantVehiculo
from .models import Customer, Address, CustomerStats


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
    selected_vehicle_marca_id = serializers.PrimaryKeyRelatedField(
        source='selected_vehicle_marca',
        queryset=Marca.objects.filter(activo=True),
        allow_null=True,
        required=False,
    )
    selected_vehicle_modelo_id = serializers.PrimaryKeyRelatedField(
        source='selected_vehicle_modelo',
        queryset=ModeloVehiculo.objects.filter(activo=True),
        allow_null=True,
        required=False,
    )
    selected_vehicle_variante_id = serializers.PrimaryKeyRelatedField(
        source='selected_vehicle_variante',
        queryset=VariantVehiculo.objects.select_related('modelo__marca', 'motor', 'transmision', 'traccion'),
        allow_null=True,
        required=False,
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
            'selected_vehicle_marca_id',
            'selected_vehicle_modelo_id',
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

    def validate(self, attrs):
        marca = attrs.get('selected_vehicle_marca', getattr(self.instance, 'selected_vehicle_marca', None))
        modelo = attrs.get('selected_vehicle_modelo', getattr(self.instance, 'selected_vehicle_modelo', None))
        variante = attrs.get('selected_vehicle_variante', getattr(self.instance, 'selected_vehicle_variante', None))

        if variante is not None:
            modelo = variante.modelo
            marca = variante.modelo.marca
            attrs['selected_vehicle_modelo'] = modelo
            attrs['selected_vehicle_marca'] = marca
        elif modelo is not None:
            marca = modelo.marca
            attrs['selected_vehicle_marca'] = marca

        if modelo is not None and marca is not None and modelo.marca_id != marca.id:
            raise serializers.ValidationError({
                'selected_vehicle_modelo_id': 'El modelo no pertenece a la marca seleccionada.'
            })

        if variante is not None and modelo is not None and variante.modelo_id != modelo.id:
            raise serializers.ValidationError({
                'selected_vehicle_variante_id': 'La variante no pertenece al modelo seleccionado.'
            })

        return attrs

    def get_selected_vehicle(self, obj):
        marca = obj.selected_vehicle_marca
        modelo = obj.selected_vehicle_modelo
        variante = obj.selected_vehicle_variante

        if not marca and not modelo and not variante:
            return None

        variante_display_name = None
        if variante:
            hasta = variante.anio_hasta or 'Actual'
            variante_display_name = (
                f"{variante.motor} | {variante.transmision} | {variante.traccion} "
                f"({variante.anio_desde}-{hasta})"
            )

        return {
            'marca_id': marca.id if marca else None,
            'marca_nombre': marca.nombre if marca else None,
            'modelo_id': modelo.id if modelo else None,
            'modelo_nombre': modelo.nombre if modelo else None,
            'variante_id': variante.id if variante else None,
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


class CustomerStatsSerializer(serializers.ModelSerializer):
    """Serializer para CustomerStats"""
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
            'preferred_brands',
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
        from django.contrib.auth.models import User
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
        from django.contrib.auth.models import User
        email = validated_data['email']
        username = email.split('@')[0]
        # Asegurar username único
        base = username
        i = 1
        while User.objects.filter(username=username).exists():
            username = f'{base}{i}'
            i += 1
        user = User.objects.create_user(
            username=username,
            email=email,
            password=validated_data['password'],
        )
        customer = Customer.objects.create(
            user=user,
            customer_type=validated_data['customer_type'],
            document_type=validated_data['document_type'],
            document_number=validated_data['document_number'],
            business_activity=validated_data.get('business_activity', ''),
        )
        return customer