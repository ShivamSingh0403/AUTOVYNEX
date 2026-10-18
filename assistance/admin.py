from django.contrib import admin
from .models import RoadsideAssistanceRequest


@admin.register(RoadsideAssistanceRequest)
class RoadsideAssistanceRequestAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'contact_name', 'request_type', 'urgency', 'status', 'city', 'assigned_patrol', 'created_at')
    list_filter = ('status', 'request_type', 'urgency', 'city')
    search_fields = ('ticket_number', 'contact_name', 'contact_phone', 'vehicle_details', 'location_address')
