from django.urls import path
from . import views

app_name = 'assistance'

urlpatterns = [
    path('', views.assistance_request_view, name='request_view'),
    path('ticket/<str:ticket_number>/', views.ticket_detail, name='ticket_detail'),
]
