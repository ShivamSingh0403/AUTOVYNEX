from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.shop_list, name='shop'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('api/search/', views.search_api, name='search_api'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:product_id>/', views.toggle_wishlist, name='toggle_wishlist'),
]
