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

    # AUTOVYNEX Part 7: Used-Car Marketplace Administration
    path('used-cars/', views.admin_used_cars, name='admin_used_cars'),
    path('used-cars/<int:car_id>/', views.admin_used_car_detail, name='admin_used_car_detail'),
    path('used-cars/<int:car_id>/action/', views.admin_used_car_action, name='admin_used_car_action'),
    path('used-cars/reports/', views.admin_used_car_reports, name='admin_used_car_reports'),
    path('used-cars/reports/<int:report_id>/action/', views.admin_used_car_report_action, name='admin_used_car_report_action'),
    path('used-cars/enquiries/', views.admin_used_car_enquiries, name='admin_used_car_enquiries'),
]
