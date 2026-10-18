from django.urls import path
from . import views

app_name = 'used_cars'

urlpatterns = [
    path('', views.marketplace_list, name='marketplace'),
    path('sell/', views.create_listing, name='create_listing'),
    path('compare/', views.compare_view, name='compare_view'),
    path('compare/clear/', views.clear_compare, name='clear_compare'),
    path('compare/toggle/<int:car_id>/', views.toggle_compare, name='toggle_compare'),
    path('<slug:slug>/', views.listing_detail, name='listing_detail'),
]
