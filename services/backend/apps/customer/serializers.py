"""
Serializers de Customer
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Customer, Address, CustomerStats


class CustomerSerializer(serializers.ModelSerializer):
    """Serializer para Customer"""
    email = serializers.EmailField(source='user.email', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    full_document = serializers.CharField(read_only=True)
    
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
            'receive_newsletter',
            'receive_promotions',
            'is_active',
            'is_verified',
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