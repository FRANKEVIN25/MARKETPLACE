"""
URLs de Customer
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, AddressViewSet, CustomerVehicleViewSet

router = DefaultRouter()
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'addresses', AddressViewSet, basename='address')
router.register(r'vehicles', CustomerVehicleViewSet, basename='customer-vehicle')

urlpatterns = [
    path('', include(router.urls)),
]