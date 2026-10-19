from django.urls import path
from . import views

app_name = 'enquiries'

urlpatterns = [
    # Customer-facing Sourcing & Enquiry Views
    path('', views.missing_part_request, name='index'),
    path('missing-part/', views.missing_part_request, name='missing_part_request'),
    path('confirmation/<str:reference_code>/', views.enquiry_confirmation, name='enquiry_confirmation'),
    path('my-enquiries/', views.my_enquiries, name='my_enquiries'),
    path('detail/<str:reference_code>/', views.enquiry_detail, name='enquiry_detail'),
    path('status/<str:reference_code>/', views.enquiry_status, name='enquiry_status'),
    path('photo/<int:image_id>/', views.secure_enquiry_photo, name='secure_photo'),
]
