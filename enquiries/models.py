import os
import uuid
import random
import string
from decimal import Decimal
from datetime import date, datetime
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


def safe_enquiry_image_path(instance, filename):
    """Generates an obfuscated, collision-free storage path for uploaded enquiry photos."""
    ext = filename.split('.')[-1].lower()
    safe_name = f"part_{uuid.uuid4().hex[:14]}.{ext}"
    return os.path.join('enquiries', 'parts', safe_name)


def generate_unique_reference():
    """Generates a guaranteed unique human-readable enquiry reference code: AVX-YYYY-XXXXXX."""
    year = date.today().year
    while True:
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        ref = f"AVX-{year}-{suffix}"
        if not MissingPartEnquiry.objects.filter(reference_code=ref).exists():
            return ref


class MissingPartEnquiry(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('info_required', 'More Information Required'),
        ('sourcing', 'Sourcing in Progress'),
        ('part_found', 'Part Found'),
        ('quote_prepared', 'Quote Prepared'),
        ('customer_accepted', 'Customer Accepted'),
        ('unavailable', 'Part Currently Unavailable'),
        ('completed', 'Completed / Sourced'),
        ('cancelled', 'Cancelled'),
    ]

    CATEGORY_CHOICES = [
        ('engine_mechanical', 'Engine & Mechanical Components'),
        ('transmission_clutch', 'Transmission, Gearbox & Clutch'),
        ('suspension_steering', 'Suspension, Steering & Axles'),
        ('braking', 'Braking System (Rotors, Calipers, ABS)'),
        ('electrical_sensors', 'Electrical, ECU, Sensors & Wiring'),
        ('body_panels', 'Body Panels, Bumpers & Trim'),
        ('cooling_hvac', 'Cooling, Radiator & Air Conditioning'),
        ('lighting', 'Headlamps, Tail Lights & Indicators'),
        ('interior', 'Interior Trims, Dashboard & Controls'),
        ('other', 'Other Specialized / Rare Assembly'),
    ]

    CONTACT_PREFERENCES = [
        ('email', 'Email Notification'),
        ('phone', 'Phone Call'),
        ('whatsapp', 'WhatsApp Notification'),
    ]

    URGENCY_CHOICES = [
        ('standard', 'Standard Sourcing (3–7 Business Days)'),
        ('express', 'Express Dispatch (1–3 Business Days)'),
        ('critical', 'Vehicle Off-Road / Urgent (Immediate Priority)'),
    ]

    QUOTE_STATUS_CHOICES = [
        ('none', 'No Quote Yet'),
        ('pending', 'Quote Pending Customer Review'),
        ('accepted', 'Quote Accepted by Customer'),
        ('declined', 'Quote Declined by Customer'),
        ('expired', 'Quote Expired'),
    ]

    # Reference & Customer Association
    reference_code = models.CharField(max_length=32, unique=True, editable=False, db_index=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='part_enquiries')
    
    # Vehicle Information (Structured)
    make = models.CharField(max_length=100, blank=True)
    model_name = models.CharField(max_length=100, blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    fuel_type = models.CharField(max_length=40, blank=True)
    variant_name = models.CharField(max_length=120, blank=True)
    registration_number = models.CharField(max_length=40, blank=True, help_text="Optional registration number for lookup")
    vin_chassis = models.CharField(max_length=50, blank=True, help_text="Confidential VIN/Chassis number for exact part matching")
    vehicle_details = models.CharField(max_length=255, blank=True, help_text="Full vehicle description string")

    # Part Information
    part_name = models.CharField(max_length=150, help_text="Name or description of the required spare part")
    category = models.CharField(max_length=60, choices=CATEGORY_CHOICES, default='engine_mechanical')
    brand_preference = models.CharField(max_length=100, blank=True, help_text="OEM or preferred manufacturer")
    part_number = models.CharField(max_length=100, blank=True, help_text="OEM Part number if known")
    description = models.TextField(help_text="Detailed symptoms, part condition, or mounting requirements")
    budget_range = models.CharField(max_length=80, blank=True, help_text="Target budget or price expectation in INR")
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default='standard')

    # Primary Photo
    damaged_part_image = models.ImageField(upload_to=safe_enquiry_image_path, blank=True, null=True, help_text="Photo of broken part or part label")

    # Contact Preferences
    contact_name = models.CharField(max_length=120)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=25)
    contact_preference = models.CharField(max_length=30, choices=CONTACT_PREFERENCES, default='email')
    whatsapp_enabled = models.BooleanField(default=False, help_text="Customer opted-in for WhatsApp status updates")

    # Sourcing Status & Workflow
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='submitted', db_index=True)
    customer_notes = models.TextField(blank=True, help_text="Customer-visible notes and logistics updates")
    internal_notes = models.TextField(blank=True, help_text="Strictly private staff notes and supplier quotes")
    admin_notes = models.TextField(blank=True, help_text="Legacy notes field")

    # Sourcing Quote Details
    quote_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Sourced part price in INR")
    quote_brand = models.CharField(max_length=120, blank=True, help_text="Confirmed supplier/brand")
    quote_part_number = models.CharField(max_length=120, blank=True, help_text="Confirmed OEM part number")
    quote_condition = models.CharField(max_length=80, blank=True, default='Brand New OEM Genuine')
    quote_delivery_days = models.CharField(max_length=80, blank=True, default='3–5 Business Days')
    quote_warranty = models.CharField(max_length=120, blank=True, default='6 Months AUTOVYNEX Warranty')
    quote_notes = models.TextField(blank=True, help_text="Special terms, core exchange, or shipping inclusions")
    quote_expires_at = models.DateTimeField(null=True, blank=True, help_text="Expiration deadline of the quote")
    quote_status = models.CharField(max_length=20, choices=QUOTE_STATUS_CHOICES, default='none')
    quote_decision_at = models.DateTimeField(null=True, blank=True)
    is_demo_quote = models.BooleanField(default=True, help_text="Clearly tags seed/demo quotes for academic compliance")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Missing Part Enquiry'
        verbose_name_plural = 'Missing Part Enquiries'

    def save(self, *args, **kwargs):
        if not self.reference_code:
            self.reference_code = generate_unique_reference()
        
        # Build comprehensive vehicle_details string if not populated
        if not self.vehicle_details:
            parts = [str(self.year) if self.year else '', self.make, self.model_name, self.variant_name, f"({self.fuel_type})" if self.fuel_type else '']
            self.vehicle_details = " ".join([p for p in parts if p]).strip() or "Vehicle Not Specified"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference_code} — {self.part_name} ({self.get_status_display()})"

    @property
    def display_vehicle(self):
        if self.vehicle_details:
            return self.vehicle_details
        parts = [str(self.year) if self.year else '', self.make, self.model_name, self.variant_name]
        return " ".join([p for p in parts if p]).strip() or "General Automotive Sourcing"

    @property
    def vehicle_display(self):
        return self.display_vehicle

    @property
    def is_quote_available(self):
        return self.quote_amount is not None and self.status in ['quote_prepared', 'customer_accepted', 'completed']

    @property
    def is_quote_expired(self):
        if not self.quote_expires_at:
            return False
        return timezone.now() > self.quote_expires_at

    @property
    def can_customer_cancel(self):
        """Customers can cancel only if enquiry is in initial review or searching/sourcing states."""
        return self.status in ['submitted', 'under_review', 'info_required', 'sourcing', 'searching']

    def can_transition_to(self, new_status, user):
        """
        Validates state machine transitions.
        Staff has broader administrative capabilities; customers can only cancel or accept/decline quotes.
        """
        if self.status == new_status:
            return True

        if not (user and user.is_staff):
            # Customer permissions
            if new_status == 'cancelled' and self.can_customer_cancel:
                return True
            if new_status == 'customer_accepted' and self.status == 'quote_prepared' and not self.is_quote_expired:
                return True
            return False

        # Staff valid transitions
        # Terminal states completed and cancelled cannot transition back to submitted
        if self.status in ['completed', 'cancelled'] and new_status in ['submitted', 'under_review']:
            return False

        return True


class EnquiryImage(models.Model):
    enquiry = models.ForeignKey(MissingPartEnquiry, on_delete=models.CASCADE, related_name='additional_images')
    image = models.ImageField(upload_to=safe_enquiry_image_path)
    caption = models.CharField(max_length=200, blank=True)
    file_size = models.PositiveIntegerField(default=0, help_text="Size in bytes")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"Photo for {self.enquiry.reference_code}"


class EnquiryStatusHistory(models.Model):
    enquiry = models.ForeignKey(MissingPartEnquiry, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=40, blank=True)
    status = models.CharField(max_length=40)
    notes = models.TextField(blank=True, help_text="Customer-visible timeline note")
    internal_notes = models.TextField(blank=True, help_text="Staff-only internal note")
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def new_status(self):
        return self.status

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Enquiry Status Histories'

    def __str__(self):
        return f"{self.enquiry.reference_code}: {self.old_status} -> {self.new_status} ({self.created_at.strftime('%d %b %Y')})"
