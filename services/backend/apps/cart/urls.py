from django.urls import path
from .views import CartViewSet

cart_list = CartViewSet.as_view({'get': 'list'})
add_line = CartViewSet.as_view({'post': 'add_line'})
update_quantity = CartViewSet.as_view({'post': 'update_quantity'})
remove_line = CartViewSet.as_view({'post': 'remove_line'})
clear_cart = CartViewSet.as_view({'post': 'clear'})

urlpatterns = [
    path('cart/', cart_list, name='cart-list'),
    path('cart/add/', add_line, name='cart-add-line'),
    path('cart/update/', update_quantity, name='cart-update-quantity'),
    path('cart/remove/', remove_line, name='cart-remove-line'),
    path('cart/clear/', clear_cart, name='cart-clear'),
]
