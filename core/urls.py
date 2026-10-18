from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('offers/', views.offers, name='offers'),
    path('tools/valuation/', views.car_valuation, name='car_valuation'),
    path('tools/fuel-calculator/', views.fuel_calculator, name='fuel_calculator'),
    path('tools/ownership-calculator/', views.ownership_calculator, name='ownership_calculator'),
    path('tools/ai-car-help/', views.ai_car_help, name='ai_car_help'),
    path('legal/privacy/', views.privacy_policy, name='privacy_policy'),
    path('legal/terms/', views.terms_conditions, name='terms_conditions'),
    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),
]
