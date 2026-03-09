"""
URLs de Vehicles
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    MarcaViewSet,
    ModeloVehiculoViewSet,
    TransmisionViewSet,
    TraccionViewSet,
    MotorViewSet,
    VariantVehiculoViewSet,
    PublicMarcaListView,
    PublicModeloListView,
    PublicVariantListView,
)

router = DefaultRouter()
router.register(r'marcas', MarcaViewSet, basename='marca')
router.register(r'modelos', ModeloVehiculoViewSet, basename='modelo')
router.register(r'transmisiones', TransmisionViewSet, basename='transmision')
router.register(r'tracciones', TraccionViewSet, basename='traccion')
router.register(r'motores', MotorViewSet, basename='motor')
router.register(r'variantes', VariantVehiculoViewSet, basename='variante')

public_patterns = [
    path('marcas/', PublicMarcaListView.as_view(), name='public-marca-list'),
    path('modelos/', PublicModeloListView.as_view(), name='public-modelo-list'),
    path('variantes/', PublicVariantListView.as_view(), name='public-variant-list'),
]

urlpatterns = [
    path('', include(router.urls)),
    path('public/', include((public_patterns, 'public-vehicles'))),
]
