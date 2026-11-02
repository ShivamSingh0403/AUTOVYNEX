from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    # Marketplace & Directory
    path('', views.service_directory, name='directory'),
    path('providers/', views.service_directory, name='providers_list'),
    path('provider/<slug:slug>/', views.provider_detail, name='provider_detail'),

    # Appointment Booking Flow
    path('book/', views.book_service, name='book'),
    path('api/slots/', views.api_get_slots, name='api_slots'),
    path('booking/<str:booking_number>/success/', views.booking_success, name='booking_success'),
    path('booking/<str:booking_number>/', views.booking_success, name='booking_success_legacy'),

    # Customer Appointments Dashboard ("My Services")
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('my-bookings/<str:booking_number>/', views.booking_detail, name='booking_detail'),
    path('my-bookings/<str:booking_number>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('my-bookings/<str:booking_number>/reschedule/', views.reschedule_booking, name='reschedule_booking'),

    # Service Provider / Workshop Portal
    path('workshop/', views.provider_dashboard, name='provider_dashboard'),
    path('workshop/status/<str:booking_number>/', views.provider_update_status, name='provider_update_status'),
    path('workshop/complete/<str:booking_number>/', views.provider_complete_booking, name='provider_complete_booking'),
    path('workshop/schedule/', views.provider_schedule_manage, name='provider_schedule_manage'),
    path('workshop/services/', views.provider_services_manage, name='provider_services_manage'),
    path('workshop/holidays/', views.provider_unavailable_dates, name='provider_unavailable_dates'),
]
