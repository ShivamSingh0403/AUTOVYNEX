from django.db import models
from django.contrib.auth.models import User
import uuid


class MissingPartEnquiry(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('searching', 'Searching for Part Across Logistics'),
        ('quote_available', 'Quote Available'),
        ('completed', 'Completed / Sourced'),
        ('unavailable', 'Part Currently Unavailable'),
    ]

    CONTACT_PREFERENCES = [
        ('whatsapp', 'WhatsApp Notification'),
        ('phone', 'Phone Call'),
        ('email', 'Email Communication'),
    ]

    reference_code = models.CharField(max_length=32, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='part_enquiries')
    
    # Vehicle Information
    vehicle_details = models.CharField(max_length=200, help_text="e.g. 2022 Hyundai Creta SX (O) Diesel AT")
    part_name = models.CharField(max_length=150, help_text="Name of the missing or rare spare part")
    category = models.CharField(max_length=100, default='Mechanical / Engine')
    part_number = models.CharField(max_length=100, blank=True, help_text="OEM Part number if known")
    vin_chassis = models.CharField(max_length=50, blank=True, help_text="Confidential VIN/Chassis number")
    description = models.TextField(help_text="Detailed problem or part description")
    damaged_part_image = models.ImageField(upload_to='missing_parts/', blank=True, null=True, help_text="Photo of damaged part or assembly")
    
    # Contact Information
    contact_name = models.CharField(max_length=120)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    contact_preference = models.CharField(max_length=30, choices=CONTACT_PREFERENCES, default='whatsapp')

    # Admin Management
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='submitted')
    quote_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Estimated quote in INR")
    admin_notes = models.TextField(blank=True, help_text="Internal notes or updates for the customer")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.reference_code:
            self.reference_code = f"AVX-ENQ-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference_code} - {self.part_name} ({self.get_status_display()})"


class EnquiryImage(models.Model):
    enquiry = models.ForeignKey(MissingPartEnquiry, on_delete=models.CASCADE, related_name='additional_images')
    image = models.ImageField(upload_to='missing_parts/additional/')
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.enquiry.reference_code}"


class EnquiryStatusHistory(models.Model):
    enquiry = models.ForeignKey(MissingPartEnquiry, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=30)
    notes = models.TextField(blank=True)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Enquiry Status Histories'

    def __str__(self):
        return f"{self.enquiry.reference_code} status changed to {self.status}"
