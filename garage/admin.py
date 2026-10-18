from django.contrib import admin
from .models import CustomerVehicle, MaintenanceRecord, MaintenanceReminder, VehicleDocument


class MaintenanceRecordInline(admin.TabularInline):
    model = MaintenanceRecord
    extra = 0


class MaintenanceReminderInline(admin.TabularInline):
    model = MaintenanceReminder
    extra = 0


class VehicleDocumentInline(admin.TabularInline):
    model = VehicleDocument
    extra = 0


@admin.register(CustomerVehicle)
class CustomerVehicleAdmin(admin.ModelAdmin):
    list_display = ('registration_number', 'user', 'variant', 'current_mileage', 'is_default')
    list_filter = ('is_default', 'variant__model__make')
    search_fields = ('registration_number', 'vin_number', 'user__username', 'nickname')
    inlines = [MaintenanceRecordInline, MaintenanceReminderInline, VehicleDocumentInline]


@admin.register(MaintenanceRecord)
class MaintenanceRecordAdmin(admin.ModelAdmin):
    list_display = ('customer_vehicle', 'service_type', 'service_date', 'mileage', 'cost', 'workshop_name')
    list_filter = ('service_type', 'service_date')


@admin.register(MaintenanceReminder)
class MaintenanceReminderAdmin(admin.ModelAdmin):
    list_display = ('title', 'customer_vehicle', 'reminder_type', 'due_date', 'is_completed')
    list_filter = ('reminder_type', 'is_completed')


@admin.register(VehicleDocument)
class VehicleDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'customer_vehicle', 'doc_type', 'expiry_date')
    list_filter = ('doc_type',)
