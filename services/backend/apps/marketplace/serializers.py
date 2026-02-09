"""
Serializers de Marketplace
ACTUALIZADO: Incluye serializer para registro de vendors con setup de Odoo
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import Provider, Member


class ProviderSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    members_count = serializers.IntegerField(source='get_members_count', read_only=True)
    products_count = serializers.IntegerField(source='get_products_count', read_only=True)
    has_odoo_setup = serializers.BooleanField(source='has_odoo_credentials', read_only=True)
    
    class Meta:
        model = Provider
        fields = [
            'id', 'name', 'slug', 'ruc', 'email', 'phone',
            'tier', 'owner', 'owner_username',
            'is_active', 'is_approved',
            'odoo_company_id', 'odoo_user_id', 'odoo_username',
            'has_odoo_setup',
            'members_count', 'products_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'slug', 'created_at', 'updated_at', 
            'odoo_company_id', 'odoo_user_id', 'odoo_username'
        ]


class MembershipSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    
    class Meta:
        model = Member
        fields = [
            'id', 'user', 'user_username', 'user_email',
            'provider', 'provider_name', 'role',
            'can_manage_products', 'can_manage_prices',
            'can_manage_stock', 'can_invite_users', 'can_sync_odoo',
            'joined_at'
        ]
        read_only_fields = ['joined_at']


# ====== NUEVO: SERIALIZER DE REGISTRO DE VENDOR ======

class VendorRegistrationSerializer(serializers.Serializer):
    """
    Serializer para registro completo de un vendor con setup automático en Odoo
    """
    # Datos del usuario Django
    username = serializers.CharField(
        max_length=150,
        help_text="Username para el marketplace"
    )
    email = serializers.EmailField(
        help_text="Email del usuario (será usado como login en Odoo)"
    )
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text="Password para el marketplace"
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text="Confirmación del password"
    )
    
    # Datos del proveedor/negocio
    business_name = serializers.CharField(
        max_length=100,
        help_text="Nombre del negocio (ej: AutoPartes ABC SAC)"
    )
    business_email = serializers.EmailField(
        required=False,
        allow_blank=True,
        help_text="Email del negocio (opcional, usa el email del usuario si no se proporciona)"
    )
    phone = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        help_text="Teléfono del negocio"
    )
    ruc = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        help_text="RUC del negocio (Perú)"
    )
    
    # Password para Odoo (separado del marketplace)
    odoo_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text="Password para acceso a Odoo (gestión de productos)"
    )
    odoo_password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text="Confirmación del password de Odoo"
    )
    
    # Tier (opcional, default: starter)
    tier = serializers.ChoiceField(
        choices=['starter', 'pro', 'premium'],
        default='starter',
        help_text="Plan de servicio"
    )
    
    # Aceptación de términos
    accept_terms = serializers.BooleanField(
        write_only=True,
        help_text="Debe aceptar los términos y condiciones"
    )
    
    def validate_username(self, value):
        """Valida que el username no exista"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Este username ya está en uso")
        return value
    
    def validate_email(self, value):
        """Valida que el email no exista"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este email ya está registrado")
        return value
    
    def validate_business_name(self, value):
        """Valida que el nombre del negocio no exista"""
        if Provider.objects.filter(name=value).exists():
            raise serializers.ValidationError("Ya existe un proveedor con este nombre")
        return value
    
    def validate_ruc(self, value):
        """Valida el formato del RUC (Perú)"""
        if value and len(value) != 11:
            raise serializers.ValidationError("El RUC debe tener 11 dígitos")
        if value and not value.isdigit():
            raise serializers.ValidationError("El RUC debe contener solo números")
        return value
    
    def validate_password(self, value):
        """Valida el password del marketplace usando Django's validators"""
        validate_password(value)
        return value
    
    def validate_odoo_password(self, value):
        """Valida el password de Odoo"""
        if len(value) < 8:
            raise serializers.ValidationError("El password de Odoo debe tener al menos 8 caracteres")
        return value
    
    def validate_accept_terms(self, value):
        """Valida que se acepten los términos"""
        if not value:
            raise serializers.ValidationError("Debe aceptar los términos y condiciones")
        return value
    
    def validate(self, data):
        """Validaciones que requieren múltiples campos"""
        # Validar que los passwords coincidan
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': "Los passwords no coinciden"
            })
        
        if data['odoo_password'] != data['odoo_password_confirm']:
            raise serializers.ValidationError({
                'odoo_password_confirm': "Los passwords de Odoo no coinciden"
            })
        
        # Si no se proporciona business_email, usar el email del usuario
        if not data.get('business_email'):
            data['business_email'] = data['email']
        
        return data
    
    def create(self, validated_data):
        """
        Este método NO crea directamente, solo retorna los datos validados
        La creación se hace en la vista usando la tarea Celery
        """
        return validated_data


class ProviderDetailSerializer(serializers.ModelSerializer):
    """
    Serializer detallado del Provider con toda la información
    """
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    owner_email = serializers.CharField(source='owner.email', read_only=True)
    members_count = serializers.IntegerField(source='get_members_count', read_only=True)
    products_count = serializers.IntegerField(source='get_products_count', read_only=True)
    has_odoo_setup = serializers.BooleanField(source='has_odoo_credentials', read_only=True)
    tier_limits = serializers.SerializerMethodField()
    usage_percentage = serializers.SerializerMethodField()
    connection_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Provider
        fields = [
            'id', 'name', 'slug', 'ruc', 'email', 'phone',
            'tier', 'owner', 'owner_username', 'owner_email',
            'is_active', 'is_approved',
            'odoo_company_id', 'odoo_user_id', 'odoo_username',
            'has_odoo_setup',
            'monthly_orders', 'total_products', 'monthly_revenue',
            'tier_limits', 'usage_percentage', 'connection_info',
            'members_count', 'products_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'slug', 'created_at', 'updated_at',
            'odoo_company_id', 'odoo_user_id', 'odoo_username'
        ]
    
    def get_tier_limits(self, obj):
        """Retorna los límites del tier actual"""
        return obj.get_tier_limits()
    
    def get_usage_percentage(self, obj):
        """Retorna el porcentaje de uso de recursos"""
        return obj.get_usage_percentage()
    
    def get_connection_info(self, obj):
        """Retorna información de conexión (sin credenciales sensibles)"""
        info = obj.get_odoo_connection_info()
        # No incluir credenciales en la respuesta
        return {
            'instance_type': info['instance_type'],
            'has_credentials': obj.has_odoo_credentials()
        }