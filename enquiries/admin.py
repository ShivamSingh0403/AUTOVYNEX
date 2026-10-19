from django.contrib import admin
from .models import MissingPartEnquiry, EnquiryImage, EnquiryStatusHistory


class EnquiryImageInline(admin.TabularInline):
    model = EnquiryImage
    extra = 1
    readonly_fields = ('file_size', 'uploaded_at')


class EnquiryStatusHistoryInline(admin.TabularInline):
    model = EnquiryStatusHistory
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('old_status', 'status', 'notes', 'internal_notes', 'changed_by', 'created_at')


@admin.register(MissingPartEnquiry)
class MissingPartEnquiryAdmin(admin.ModelAdmin):
    list_display = (
        'reference_code', 'part_name', 'category', 'display_vehicle',
        'contact_name', 'status', 'quote_amount', 'quote_status', 'created_at'
    )
    list_filter = ('status', 'category', 'urgency', 'quote_status', 'created_at')
    search_fields = (
        'reference_code', 'part_name', 'part_number', 'vin_chassis',
        'contact_name', 'contact_phone', 'contact_email', 'make', 'model_name'
    )
    readonly_fields = ('reference_code', 'created_at', 'updated_at')
    inlines = [EnquiryImageInline, EnquiryStatusHistoryInline]
    fieldsets = (
        ('Enquiry Metadata', {
            'fields': ('reference_code', 'user', 'status', 'created_at', 'updated_at')
        }),
        ('Vehicle Specifications', {
            'fields': ('make', 'model_name', 'year', 'fuel_type', 'variant_name', 'registration_number', 'vin_chassis', 'vehicle_details')
        }),
        ('Part Specifications', {
            'fields': ('part_name', 'category', 'brand_preference', 'part_number', 'description', 'budget_range', 'urgency', 'damaged_part_image')
        }),
        ('Customer Contact Preferences', {
            'fields': ('contact_name', 'contact_email', 'contact_phone', 'contact_preference', 'whatsapp_enabled')
        }),
        ('Sourcing Notes', {
            'fields': ('customer_notes', 'internal_notes', 'admin_notes')
        }),
        ('Official Sourcing Quote', {
            'fields': (
                'quote_amount', 'quote_brand', 'quote_part_number', 'quote_condition',
                'quote_delivery_days', 'quote_warranty', 'quote_notes',
                'quote_expires_at', 'quote_status', 'quote_decision_at', 'is_demo_quote'
            )
        }),
    )


@admin.register(EnquiryImage)
class EnquiryImageAdmin(admin.ModelAdmin):
    list_display = ('enquiry', 'caption', 'file_size', 'uploaded_at')
    search_fields = ('enquiry__reference_code', 'caption')


@admin.register(EnquiryStatusHistory)
class EnquiryStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('enquiry', 'old_status', 'status', 'changed_by', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('enquiry__reference_code', 'notes', 'internal_notes')
