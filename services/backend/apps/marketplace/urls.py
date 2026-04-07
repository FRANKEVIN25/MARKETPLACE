"""
URLs de Marketplace
ACTUALIZADO: Incluye endpoints de registro y gestión de providers
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'providers', views.ProviderViewSet, basename='provider')
router.register(r'members', views.MemberViewSet, basename='member')

urlpatterns = [
    # Endpoint público de registro
    path('register-vendor/', views.register_vendor, name='register-vendor'),
    
    # Verificar estado de registro
    path('registration-status/<str:task_id>/', views.check_registration_status, name='registration-status'),

    # ViewSets
    path('', include(router.urls)),
]