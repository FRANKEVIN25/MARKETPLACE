"""
Permisos personalizados para Multi-Tenancy
"""
from rest_framework import permissions

class IsProviderAdmin(permissions.BasePermission):
    """
    Permiso: Solo admin del proveedor.
    """
    message = "Solo administradores del grupo pueden realizar esta acción."
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        membership = getattr(request, 'current_membership', None)
        return membership and membership.role == 'admin'
    
class CanManageProducts(permissions.BasePermission):
    """
    Permiso: Puede gestionar productos de su grupo.
    """
    message = "No tienes permiso para gestionar productos."
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        # Métodos seguros siempre permitidos (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            return True
        membership = getattr(request, 'current_membership', None)
        return membership and membership.can_manage_products
    


class BelongsToGroup(permissions.BasePermission):
    """
    Permiso: El objeto pertenece al grupo del usuario.
    """
    message = "Este objeto no pertenece a tu grupo."
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        current_provider = getattr(request, 'current_provider', None)
        if not current_provider:
            return False
        # El objeto debe tener un campo 'provider'
        return hasattr(obj, 'provider') and obj.provider == current_provider