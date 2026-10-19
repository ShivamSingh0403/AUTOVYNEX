from django.urls import path
from . import views

app_name = 'garage'

urlpatterns = [
    # 1. Garage Fleet Dashboard
    path('', views.garage_index, name='index'),
    
    # 2. Vehicle Management
    path('add/', views.add_vehicle, name='add_vehicle'),
    path('vehicle/<int:vehicle_id>/', views.vehicle_detail, name='vehicle_detail'),
    path('vehicle/<int:vehicle_id>/edit/', views.edit_vehicle, name='edit_vehicle'),
    path('vehicle/<int:vehicle_id>/delete/', views.delete_vehicle, name='delete_vehicle'),
    path('vehicle/<int:vehicle_id>/update-odometer/', views.update_odometer, name='update_odometer'),
    path('vehicle/<int:vehicle_id>/set-default/', views.set_default_vehicle, name='set_default'),
    
    # 3. Service Records
    path('vehicle/<int:vehicle_id>/add-record/', views.add_maintenance_record, name='add_record'),
    path('record/<int:record_id>/edit/', views.edit_maintenance_record, name='edit_record'),
    path('record/<int:record_id>/delete/', views.delete_maintenance_record, name='delete_record'),
    path('record/<int:record_id>/invoice/', views.view_record_invoice, name='view_invoice'),
    
    # 4. Maintenance Reminders
    path('vehicle/<int:vehicle_id>/add-reminder/', views.add_reminder, name='add_reminder'),
    path('reminder/<int:reminder_id>/edit/', views.edit_reminder, name='edit_reminder'),
    path('reminder/<int:reminder_id>/delete/', views.delete_reminder, name='delete_reminder'),
    path('reminder/<int:reminder_id>/toggle/', views.toggle_reminder, name='toggle_reminder'),
    path('reminder/<int:reminder_id>/postpone/', views.postpone_reminder, name='postpone_reminder'),
    
    # 5. Document Vault
    path('vehicle/<int:vehicle_id>/upload-doc/', views.upload_document, name='upload_document'),
    path('document/<int:doc_id>/view/', views.secure_view_document, name='view_document'),
    path('document/<int:doc_id>/download/', views.secure_download_document, name='download_document'),
    path('document/<int:doc_id>/delete/', views.delete_document, name='delete_document'),

    # 6. Expenses & Analytics Dashboard
    path('expenses/', views.expense_dashboard, name='expense_dashboard'),
    path('expenses/<int:vehicle_id>/', views.expense_dashboard, name='vehicle_expenses'),
]
