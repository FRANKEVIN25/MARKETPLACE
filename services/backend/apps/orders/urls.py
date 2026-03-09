"""
URLs para Orders API
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, SubOrderViewSet, VendorOrderViewSet, OdooWebhookView

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'suborders', SubOrderViewSet, basename='suborder')
router.register(r'vendor/orders', VendorOrderViewSet, basename='vendor-order')
router.register(r'odoo-webhook', OdooWebhookView, basename='odoo-webhook')

urlpatterns = [
    path('', include(router.urls)),
]
