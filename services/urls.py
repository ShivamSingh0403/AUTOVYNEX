from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    path('providers/', views.service_directory, name='directory'),
    path('book/', views.book_service, name='book'),
    path('booking/<str:booking_number>/', views.booking_success, name='booking_success'),
    path('booking/<str:booking_number>/cancel/', views.cancel_booking, name='cancel_booking'),
]
