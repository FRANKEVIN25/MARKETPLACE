"""
URLs públicas de servicios de taller.
"""
from django.urls import path

from .views import (
    PublicServiceCategoryListView,
    PublicServiceDetailView,
    PublicServiceListingListView,
    PublicWorkshopDetailView,
    PublicWorkshopLocationOptionsView,
)

urlpatterns = [
    path('categories/', PublicServiceCategoryListView.as_view(), name='service-category-list'),
    path('listings/', PublicServiceListingListView.as_view(), name='service-listing-list'),
    path('locations/', PublicWorkshopLocationOptionsView.as_view(), name='workshop-location-options'),
    path('services/<int:pk>/', PublicServiceDetailView.as_view(), name='service-detail'),
    path('workshops/<int:pk>/', PublicWorkshopDetailView.as_view(), name='workshop-detail'),
]
