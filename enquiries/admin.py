from django.contrib import admin
from .models import MissingPartEnquiry


@admin.register(MissingPartEnquiry)
class MissingPartEnquiryAdmin(admin.ModelAdmin):
    list_display = ('reference_code', 'part_name', 'vehicle_details', 'contact_name', 'status', 'quote_amount', 'created_at')
    list_filter = ('status', 'category', 'created_at')
    search_fields = ('reference_code', 'part_name', 'part_number', 'vin_chassis', 'contact_name', 'contact_phone')
