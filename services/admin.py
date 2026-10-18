from django.contrib import admin
from .models import ServiceProvider, Service, ServiceBooking, InstallationRequest


@admin.register(ServiceProvider)
class ServiceProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'rating', 'total_reviews', 'contact_number', 'verified', 'is_active')
    list_filter = ('city', 'verified', 'is_active')
    search_fields = ('name', 'city', 'address')


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'estimated_duration', 'starting_price', 'is_popular')
    list_filter = ('category', 'is_popular')
    search_fields = ('name',)


@admin.register(ServiceBooking)
class ServiceBookingAdmin(admin.ModelAdmin):
    list_display = ('booking_number', 'user', 'provider', 'service', 'booking_date', 'time_slot', 'status')
    list_filter = ('status', 'booking_date', 'provider')
    search_fields = ('booking_number', 'user__username', 'vehicle_info', 'customer_phone')


@admin.register(InstallationRequest)
class InstallationRequestAdmin(admin.ModelAdmin):
    list_display = ('request_number', 'user', 'product_name', 'status', 'created_at')
    list_filter = ('status',)
