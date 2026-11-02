from django.contrib import admin
from .models import (
    ServiceCategory, ServiceProvider, Service, ProviderService,
    ProviderSchedule, ProviderUnavailableDate, ServiceBooking,
    ServiceBookingHistory, ServiceCompletionRecord, ServiceEnquiry,
    InstallationRequest
)


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon_name', 'sort_order', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')
    list_filter = ('is_active',)


@admin.register(ServiceProvider)
class ServiceProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'state', 'status', 'is_demo', 'is_verified', 'contact_number', 'is_active')
    list_filter = ('city', 'status', 'is_demo', 'is_verified', 'is_active')
    search_fields = ('name', 'city', 'postal_code', 'address')
    filter_horizontal = ('supported_brands',)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_ref', 'estimated_duration', 'starting_price', 'is_popular', 'is_active')
    list_filter = ('category_ref', 'is_popular', 'is_active')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(ProviderService)
class ProviderServiceAdmin(admin.ModelAdmin):
    list_display = ('provider', 'service', 'price', 'duration_minutes', 'is_available')
    list_filter = ('provider', 'is_available')
    search_fields = ('provider__name', 'service__name')


@admin.register(ProviderSchedule)
class ProviderScheduleAdmin(admin.ModelAdmin):
    list_display = ('provider', 'get_weekday_display', 'is_closed', 'open_time', 'close_time', 'slot_duration_minutes', 'max_bookings_per_slot')
    list_filter = ('provider', 'weekday', 'is_closed')


@admin.register(ProviderUnavailableDate)
class ProviderUnavailableDateAdmin(admin.ModelAdmin):
    list_display = ('provider', 'date', 'reason')
    list_filter = ('provider', 'date')
    search_fields = ('provider__name', 'reason')


@admin.register(ServiceBooking)
class ServiceBookingAdmin(admin.ModelAdmin):
    list_display = ('booking_number', 'user', 'provider', 'service', 'booking_date', 'time_slot', 'status', 'payment_status', 'estimated_cost', 'final_amount')
    list_filter = ('status', 'payment_status', 'booking_date', 'provider')
    search_fields = ('booking_number', 'user__username', 'vehicle_info', 'customer_phone')


@admin.register(ServiceBookingHistory)
class ServiceBookingHistoryAdmin(admin.ModelAdmin):
    list_display = ('booking', 'previous_status', 'new_status', 'changed_by', 'created_at')
    list_filter = ('new_status', 'created_at')
    search_fields = ('booking__booking_number', 'customer_note')


@admin.register(ServiceCompletionRecord)
class ServiceCompletionRecordAdmin(admin.ModelAdmin):
    list_display = ('booking', 'final_amount', 'odometer_reading', 'completed_at', 'linked_maintenance_record')
    search_fields = ('booking__booking_number', 'work_performed', 'parts_replaced')


@admin.register(ServiceEnquiry)
class ServiceEnquiryAdmin(admin.ModelAdmin):
    list_display = ('provider', 'name', 'phone', 'email', 'is_responded', 'created_at')
    list_filter = ('is_responded', 'created_at', 'provider')
    search_fields = ('name', 'phone', 'email', 'message')


@admin.register(InstallationRequest)
class InstallationRequestAdmin(admin.ModelAdmin):
    list_display = ('request_number', 'user', 'product_name', 'status', 'created_at')
    list_filter = ('status',)
