from django.urls import path
from . import views

app_name = 'custom_admin'

urlpatterns = [
    path('', views.dashboard_overview, name='dashboard_overview'),
    path('orders/', views.admin_orders, name='admin_orders'),
    path('orders/<int:order_id>/', views.admin_order_update, name='admin_order_update'),
    path('inventory/', views.admin_inventory, name='admin_inventory'),
    path('enquiries/', views.admin_enquiries, name='admin_enquiries'),
    path('enquiries/<int:enquiry_id>/', views.admin_enquiry_update, name='admin_enquiry_update'),
    path('services/', views.admin_services, name='admin_services'),
    path('assistance/', views.admin_assistance, name='admin_assistance'),
]
