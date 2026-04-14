"""
URLs de Products
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet, ProductViewSet, MarketplaceProductViewSet,
    StoreViewSet, PublicCategoryListView
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'marketplace', MarketplaceProductViewSet, basename='marketplace-product')
router.register(r'stores', StoreViewSet, basename='store')

urlpatterns = [
    path('', include(router.urls)),
    path('public/categories/', PublicCategoryListView.as_view(), name='public-category-list'),
]
