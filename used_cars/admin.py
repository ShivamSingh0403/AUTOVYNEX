from django.contrib import admin
from .models import UsedCarListing, CarComparison, CarValuationRecord


@admin.register(UsedCarListing)
class UsedCarListingAdmin(admin.ModelAdmin):
    list_display = ('title', 'make_name', 'model_name', 'year', 'expected_price', 'mileage', 'location_city', 'is_approved', 'is_sold')
    list_filter = ('make_name', 'fuel_type', 'transmission', 'is_approved', 'is_sold')
    search_fields = ('title', 'make_name', 'model_name', 'location_city')
    prepopulated_fields = {'slug': ('title',)}


@admin.register(CarComparison)
class CarComparisonAdmin(admin.ModelAdmin):
    list_display = ('session_key', 'user', 'created_at')


@admin.register(CarValuationRecord)
class CarValuationRecordAdmin(admin.ModelAdmin):
    list_display = ('make_name', 'model_name', 'year', 'mileage', 'estimated_price_min', 'estimated_price_max', 'created_at')
    list_filter = ('make_name', 'year', 'condition')
    search_fields = ('make_name', 'model_name')
