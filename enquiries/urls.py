from django.urls import path
from . import views

app_name = 'enquiries'

urlpatterns = [
    path('missing-part/', views.missing_part_request, name='missing_part_request'),
    path('status/<str:reference_code>/', views.enquiry_status, name='enquiry_status'),
]
