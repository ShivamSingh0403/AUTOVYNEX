from django.urls import path
from . import views

app_name = 'garage'

urlpatterns = [
    path('', views.garage_index, name='index'),
    path('add/', views.add_vehicle, name='add_vehicle'),
    path('vehicle/<int:vehicle_id>/', views.vehicle_detail, name='vehicle_detail'),
    path('vehicle/<int:vehicle_id>/set-default/', views.set_default_vehicle, name='set_default'),
    path('vehicle/<int:vehicle_id>/add-record/', views.add_maintenance_record, name='add_record'),
    path('vehicle/<int:vehicle_id>/add-reminder/', views.add_reminder, name='add_reminder'),
    path('reminder/<int:reminder_id>/toggle/', views.toggle_reminder, name='toggle_reminder'),
    path('vehicle/<int:vehicle_id>/upload-doc/', views.upload_document, name='upload_document'),
]
