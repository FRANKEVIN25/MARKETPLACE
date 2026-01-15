"""
Serializers de Marketplace
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Provider, Member


class ProviderSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    members_count = serializers.IntegerField(source='get_members_count', read_only=True)
    products_count = serializers.IntegerField(source='get_products_count', read_only=True)
    
    class Meta:
        model = Provider
        fields = [
            'id', 'name', 'slug', 'ruc', 'email', 'phone',
            'owner', 'owner_username',
            'is_active', 'is_approved',
            'odoo_company_id',
            'members_count', 'products_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at', 'odoo_company_id']


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