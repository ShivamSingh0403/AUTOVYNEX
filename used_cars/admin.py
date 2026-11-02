from django.contrib import admin
from django.utils.html import format_html
from .models import (
    UsedCarListing,
    UsedCarImage,
    UsedCarWishlist,
    CarComparison,
    UsedCarEnquiry,
    UsedCarReport,
    UsedCarAdminLog,
    CarValuationRecord
)


class UsedCarImageInline(admin.TabularInline):
    model = UsedCarImage
    extra = 1
    fields = ('image', 'photo_type', 'caption', 'is_primary')


class UsedCarEnquiryInline(admin.TabularInline):
    model = UsedCarEnquiry
    extra = 0
    readonly_fields = ('reference_code', 'sender_name', 'sender_email', 'sender_phone', 'enquiry_type', 'offer_amount', 'created_at')
    can_delete = False


@admin.register(UsedCarListing)
class UsedCarListingAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'seller', 'make_name', 'model_name', 'year',
        'expected_price', 'mileage', 'status', 'is_verified',
        'is_approved', 'is_sold', 'is_sample_listing', 'created_at'
    )
    list_filter = ('status', 'make_name', 'fuel_type', 'transmission', 'condition', 'is_verified', 'is_sample_listing', 'is_sold')
    search_fields = ('title', 'make_name', 'model_name', 'location_city', 'seller__username', 'seller__email')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [UsedCarImageInline, UsedCarEnquiryInline]
    actions = ['approve_listings', 'reject_listings', 'mark_as_sold']

    @admin.action(description="Approve and Publish selected listings")
    def approve_listings(self, request, queryset):
        queryset.update(status='published', is_approved=True)
        self.message_user(request, f"{queryset.count()} listings approved and published.")

    @admin.action(description="Reject selected listings")
    def reject_listings(self, request, queryset):
        queryset.update(status='rejected', is_approved=False)
        self.message_user(request, f"{queryset.count()} listings marked as rejected.")

    @admin.action(description="Mark selected listings as Sold")
    def mark_as_sold(self, request, queryset):
        queryset.update(status='sold', is_sold=True)
        self.message_user(request, f"{queryset.count()} listings marked as sold.")


@admin.register(UsedCarImage)
class UsedCarImageAdmin(admin.ModelAdmin):
    list_display = ('listing', 'photo_type', 'caption', 'is_primary', 'uploaded_at')
    list_filter = ('photo_type', 'is_primary')


@admin.register(UsedCarWishlist)
class UsedCarWishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'listing', 'added_at')
    search_fields = ('user__username', 'listing__title')


@admin.register(CarComparison)
class CarComparisonAdmin(admin.ModelAdmin):
    list_display = ('session_key', 'user', 'created_at')


@admin.register(UsedCarEnquiry)
class UsedCarEnquiryAdmin(admin.ModelAdmin):
    list_display = ('reference_code', 'listing', 'sender_name', 'sender_email', 'sender_phone', 'enquiry_type', 'status', 'created_at')
    list_filter = ('status', 'enquiry_type', 'created_at')
    search_fields = ('reference_code', 'sender_name', 'sender_email', 'listing__title')


@admin.register(UsedCarReport)
class UsedCarReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'listing', 'reason', 'status', 'reporter_name', 'created_at')
    list_filter = ('status', 'reason')
    search_fields = ('listing__title', 'details', 'reporter_name')


@admin.register(UsedCarAdminLog)
class UsedCarAdminLogAdmin(admin.ModelAdmin):
    list_display = ('admin_user', 'listing', 'action', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('admin_user__username', 'listing__title', 'notes')


@admin.register(CarValuationRecord)
class CarValuationRecordAdmin(admin.ModelAdmin):
    list_display = ('make_name', 'model_name', 'year', 'mileage', 'estimated_price_min', 'estimated_price_max', 'fair_market_value', 'user', 'created_at')
    list_filter = ('make_name', 'year', 'condition')
    search_fields = ('make_name', 'model_name')
