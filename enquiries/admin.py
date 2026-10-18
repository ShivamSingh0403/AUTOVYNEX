from django.contrib import admin
from .models import MissingPartEnquiry, EnquiryImage, EnquiryStatusHistory


class EnquiryImageInline(admin.TabularInline):
    model = EnquiryImage
    extra = 1


class EnquiryStatusHistoryInline(admin.TabularInline):
    model = EnquiryStatusHistory
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(MissingPartEnquiry)
class MissingPartEnquiryAdmin(admin.ModelAdmin):
    list_display = ('reference_code', 'part_name', 'vehicle_details', 'contact_name', 'status', 'quote_amount', 'created_at')
    list_filter = ('status', 'category', 'created_at')
    search_fields = ('reference_code', 'part_name', 'part_number', 'vin_chassis', 'contact_name', 'contact_phone')
    inlines = [EnquiryImageInline, EnquiryStatusHistoryInline]


@admin.register(EnquiryImage)
class EnquiryImageAdmin(admin.ModelAdmin):
    list_display = ('enquiry', 'caption', 'uploaded_at')


@admin.register(EnquiryStatusHistory)
class EnquiryStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('enquiry', 'status', 'changed_by', 'created_at')
    list_filter = ('status', 'created_at')
