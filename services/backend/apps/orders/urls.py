"""
URLs de Orders
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, SupplierOrderViewSet, OrderItemViewSet

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'supplier-orders', SupplierOrderViewSet, basename='supplier-order')
router.register(r'order-items', OrderItemViewSet, basename='order-item')

urlpatterns = [
    path('', include(router.urls)),
]
