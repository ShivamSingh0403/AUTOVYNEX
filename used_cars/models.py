from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
import uuid


class UsedCarListing(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_review', 'Pending Review'),
        ('published', 'Published'),
        ('rejected', 'Rejected'),
        ('sold', 'Sold'),
        ('inactive', 'Inactive'),
    ]

    FUEL_CHOICES = [
        ('Petrol', 'Petrol'),
        ('Diesel', 'Diesel'),
        ('CNG', 'CNG'),
        ('EV', 'Electric (EV)'),
        ('Hybrid', 'Hybrid'),
        ('LPG', 'LPG'),
    ]

    TRANSMISSION_CHOICES = [
        ('Manual', 'Manual'),
        ('Automatic', 'Automatic'),
    ]

    CONDITION_CHOICES = [
        ('excellent', 'Excellent (Meticulously maintained, showroom condition)'),
        ('very_good', 'Very Good (Minor cosmetic wear, pristine powertrain)'),
        ('good', 'Good (Normal age-related wear, fully reliable)'),
        ('fair', 'Fair (Requires minor maintenance or aesthetic repair)'),
        ('needs_repair', 'Needs Repair (Requires mechanical or bodywork)'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=230, unique=True, blank=True)
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='car_listings')
    make_name = models.CharField(max_length=80)
    model_name = models.CharField(max_length=80)
    variant_name = models.CharField(max_length=100, blank=True)
    year = models.PositiveIntegerField(default=2021, help_text="Manufacturing year")
    registration_year = models.PositiveIntegerField(null=True, blank=True, help_text="Registration year if known")
    mileage = models.PositiveIntegerField(help_text="Odometer reading in KM")
    fuel_type = models.CharField(max_length=20, choices=FUEL_CHOICES, default='Petrol')
    transmission = models.CharField(max_length=20, choices=TRANSMISSION_CHOICES, default='Manual')
    owners_count = models.PositiveIntegerField(default=1, null=True, blank=True, help_text="Number of previous owners")
    condition = models.CharField(max_length=30, choices=CONDITION_CHOICES, default='good', help_text="Seller-reported vehicle condition")
    condition_rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.0, null=True, blank=True, help_text="Inspection score out of 5.0")
    expected_price = models.DecimalField(max_digits=12, decimal_places=2, help_text="Asking price in INR")
    location_city = models.CharField(max_length=80, default='Bengaluru')
    location_state = models.CharField(max_length=80, default='Karnataka')
    location_area = models.CharField(max_length=100, blank=True, help_text="Locality / Area (e.g. Indiranagar, Whitefield)")
    registration_state = models.CharField(max_length=50, default='Karnataka (KA)')
    insurance_valid_till = models.DateField(blank=True, null=True)
    description = models.TextField()
    primary_image = models.ImageField(upload_to='used_cars/', blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='published', help_text="Moderation and publication state")
    rejection_reason = models.TextField(blank=True, help_text="Staff moderation reason if rejected")
    is_verified = models.BooleanField(default=False, help_text="Inspected & certified by AUTOVYNEX workshop")
    is_approved = models.BooleanField(default=True, help_text="Admin moderation approval (True for published listings)")
    is_sold = models.BooleanField(default=False)
    is_sample_listing = models.BooleanField(default=False, help_text="Differentiates sample listings from genuine seller listings")
    allow_phone_contact = models.BooleanField(default=False, help_text="Seller gives permission to display phone contact")
    contact_phone = models.CharField(max_length=20, blank=True, help_text="Seller contact phone (private unless permission granted)")
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.make_name}-{self.model_name}-{self.year}-{uuid.uuid4().hex[:6]}")
        # Sync boolean flags with status
        if self.status == 'published':
            self.is_approved = True
            self.is_sold = False
        elif self.status == 'sold':
            self.is_sold = True
        elif self.status in ('draft', 'pending_review', 'rejected', 'inactive'):
            self.is_approved = False
        super().save(*args, **kwargs)

    @property
    def is_publicly_visible(self):
        return self.status == 'published' and self.is_approved and not self.is_sold

    @property
    def formatted_inr_price(self):
        val = float(self.expected_price)
        if val >= 10000000:
            return f"₹{val / 10000000:.2f} Cr"
        elif val >= 100000:
            return f"₹{val / 100000:.2f} Lakh"
        return f"₹{val:,.0f}"

    def __str__(self):
        return f"{self.year} {self.make_name} {self.model_name} {self.variant_name} (₹{self.expected_price:,.0f})"


class UsedCarImage(models.Model):
    PHOTO_TYPE_CHOICES = [
        ('exterior', 'Exterior View'),
        ('interior', 'Interior & Cockpit'),
        ('engine', 'Engine & Powertrain'),
        ('boot', 'Boot / Trunk Space'),
        ('tyres', 'Tyres & Wheels'),
        ('document', 'RC / Service Records'),
        ('other', 'Other Detail'),
    ]

    listing = models.ForeignKey(UsedCarListing, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='used_cars/gallery/')
    photo_type = models.CharField(max_length=30, choices=PHOTO_TYPE_CHOICES, default='exterior')
    caption = models.CharField(max_length=150, blank=True)
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', 'id']

    def __str__(self):
        return f"Photo ({self.get_photo_type_display()}) for {self.listing.title}"


class UsedCarWishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='used_car_wishlist')
    listing = models.ForeignKey(UsedCarListing, on_delete=models.CASCADE, related_name='wishlisted_by')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'listing')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.username} saved {self.listing.title}"


class CarComparison(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='comparisons')
    session_key = models.CharField(max_length=64, db_index=True)
    listings = models.ManyToManyField(UsedCarListing, related_name='in_comparisons')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comparison session {self.session_key[:8]}"


class UsedCarEnquiry(models.Model):
    ENQUIRY_TYPE_CHOICES = [
        ('general', 'General Vehicle Question'),
        ('inspection', 'Request Inspection & History Details'),
        ('photos', 'Request Additional Photographs'),
        ('offer', 'Purchase Offer / Price Negotiation'),
    ]

    STATUS_CHOICES = [
        ('new', 'New'),
        ('in_review', 'In Review'),
        ('contacted', 'Seller Responded'),
        ('closed', 'Closed'),
    ]

    listing = models.ForeignKey(UsedCarListing, on_delete=models.CASCADE, related_name='enquiries')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_car_enquiries')
    sender_name = models.CharField(max_length=100)
    sender_email = models.EmailField()
    sender_phone = models.CharField(max_length=20)
    enquiry_type = models.CharField(max_length=20, choices=ENQUIRY_TYPE_CHOICES, default='general')
    offer_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    seller_reply = models.TextField(blank=True, help_text="Seller private reply or communication notes")
    seller_notes = models.TextField(blank=True, help_text="Internal notes for seller follow-up")
    reference_code = models.CharField(max_length=32, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.reference_code:
            self.reference_code = f"AVX-ENQ-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Enquiry {self.reference_code} for {self.listing.title} from {self.sender_name}"


class UsedCarReport(models.Model):
    REPORT_REASON_CHOICES = [
        ('misleading', 'Misleading Information or Specs'),
        ('fake_price', 'Incorrect or Suspicious Price'),
        ('duplicate', 'Duplicate Listing'),
        ('fraud', 'Suspected Fraud or Scam'),
        ('offensive', 'Inappropriate or Offensive Content'),
        ('sold', 'Vehicle Already Sold'),
        ('other', 'Other Reason'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('investigated', 'Investigated'),
        ('dismissed', 'Dismissed'),
        ('action_taken', 'Action Taken (Listing Moderated)'),
    ]

    listing = models.ForeignKey(UsedCarListing, on_delete=models.CASCADE, related_name='reports')
    reporter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='submitted_car_reports')
    reporter_name = models.CharField(max_length=100, blank=True)
    reporter_email = models.EmailField(blank=True)
    reason = models.CharField(max_length=40, choices=REPORT_REASON_CHOICES)
    details = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Report #{self.id} on {self.listing.title} ({self.get_reason_display()})"


class UsedCarAdminLog(models.Model):
    admin_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='used_car_admin_actions')
    listing = models.ForeignKey(UsedCarListing, on_delete=models.SET_NULL, null=True, blank=True, related_name='admin_logs')
    action = models.CharField(max_length=60)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.admin_user.username} {self.action} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class CarValuationRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='car_valuations')
    make_name = models.CharField(max_length=80)
    model_name = models.CharField(max_length=80)
    variant_name = models.CharField(max_length=100, blank=True)
    year = models.PositiveIntegerField()
    mileage = models.PositiveIntegerField(help_text="Odometer in KM")
    fuel_type = models.CharField(max_length=30)
    transmission = models.CharField(max_length=30)
    owners_count = models.PositiveIntegerField(default=1)
    condition = models.CharField(max_length=30, choices=[
        ('excellent', 'Excellent'),
        ('very_good', 'Very Good'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('needs_repair', 'Needs Repair'),
    ], default='good')
    city = models.CharField(max_length=80, blank=True, default='Bengaluru')
    original_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Original invoice price if provided")
    estimated_price_min = models.DecimalField(max_digits=12, decimal_places=2, help_text="Lower bound estimate in INR")
    estimated_price_max = models.DecimalField(max_digits=12, decimal_places=2, help_text="Upper bound estimate in INR")
    fair_market_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Midpoint fair market estimate in INR")
    factors_summary = models.TextField(blank=True, help_text="JSON serialized breakdown of valuation factors")
    comparable_count = models.PositiveIntegerField(default=0, help_text="Number of comparable marketplace listings considered")
    comparable_avg_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_estimate_only = models.BooleanField(default=True, help_text="Market estimate only; not a guaranteed purchase offer")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Valuation: {self.year} {self.make_name} {self.model_name} (₹{self.estimated_price_min:,.0f} - ₹{self.estimated_price_max:,.0f})"
