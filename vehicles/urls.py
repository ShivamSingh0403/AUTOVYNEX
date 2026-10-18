from django.urls import path
from . import views

app_name = 'vehicles'

urlpatterns = [
    path('selector/', views.vehicle_selector_page, name='selector_page'),
    path('api/models/', views.api_models_by_make, name='api_models'),
    path('api/years/', views.api_years_by_model, name='api_years'),
    path('api/fuels/', views.api_fuels_by_model_and_year, name='api_fuels'),
    path('api/variants/', views.api_variants_by_model, name='api_variants'),
    path('select-session/', views.select_vehicle_session, name='select_vehicle_session'),
    path('clear-session/', views.clear_vehicle_session, name='clear_vehicle_session'),
]
