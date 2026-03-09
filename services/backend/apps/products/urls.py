"""
URLs de Products
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet, ProductViewSet, MarketplaceProductViewSet,
    WarehouseViewSet, StockItemViewSet, PublicCategoryListView
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'marketplace', MarketplaceProductViewSet, basename='marketplace-product')
router.register(r'warehouses', WarehouseViewSet, basename='warehouse')
router.register(r'stock', StockItemViewSet, basename='stock-item')

urlpatterns = [
    path('', include(router.urls)),
    # Categorías públicas para filtros del marketplace
    path('public/categories/', PublicCategoryListView.as_view(), name='public-category-list'),
]