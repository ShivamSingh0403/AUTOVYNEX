from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
import uuid


class UsedCarListing(models.Model):
    FUEL_CHOICES = [
        ('Petrol', 'Petrol'),
        ('Diesel', 'Diesel'),
        ('CNG', 'CNG'),
        ('EV', 'Electric (EV)'),
        ('Hybrid', 'Hybrid'),
    ]

    TRANSMISSION_CHOICES = [
        ('Manual', 'Manual'),
        ('Automatic', 'Automatic'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=230, unique=True, blank=True)
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='car_listings')
    make_name = models.CharField(max_length=80)
    model_name = models.CharField(max_length=80)
    variant_name = models.CharField(max_length=100)
    year = models.PositiveIntegerField(default=2021)
    mileage = models.PositiveIntegerField(help_text="Odometer reading in KM")
    fuel_type = models.CharField(max_length=20, choices=FUEL_CHOICES, default='Petrol')
    transmission = models.CharField(max_length=20, choices=TRANSMISSION_CHOICES, default='Manual')
    owners_count = models.PositiveIntegerField(default=1, help_text="Number of previous owners")
    expected_price = models.DecimalField(max_digits=12, decimal_places=2, help_text="Price in INR")
    location_city = models.CharField(max_length=80, default='Bengaluru')
    registration_state = models.CharField(max_length=50, default='Karnataka (KA)')
    insurance_valid_till = models.DateField(blank=True, null=True)
    condition_rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.5, help_text="Inspection score out of 5.0")
    description = models.TextField()
    primary_image = models.ImageField(upload_to='used_cars/', blank=True, null=True)
    
    is_verified = models.BooleanField(default=True, help_text="Inspected & certified demo badge")
    is_approved = models.BooleanField(default=True, help_text="Admin moderation approval")
    is_sold = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.make_name}-{self.model_name}-{self.year}-{uuid.uuid4().hex[:6]}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.year} {self.make_name} {self.model_name} {self.variant_name} (₹{self.expected_price:,.0f})"


class CarComparison(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='comparisons')
    session_key = models.CharField(max_length=64, db_index=True)
    listings = models.ManyToManyField(UsedCarListing, related_name='in_comparisons')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comparison session {self.session_key[:8]}"


class CarValuationRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='car_valuations')
    make_name = models.CharField(max_length=80)
    model_name = models.CharField(max_length=80)
    year = models.PositiveIntegerField()
    mileage = models.PositiveIntegerField(help_text="Odometer in KM")
    fuel_type = models.CharField(max_length=30)
    transmission = models.CharField(max_length=30)
    condition = models.CharField(max_length=30, choices=[('excellent', 'Excellent'), ('good', 'Good'), ('fair', 'Fair')], default='good')
    estimated_price_min = models.DecimalField(max_digits=12, decimal_places=2, help_text="Lower bound estimate in INR")
    estimated_price_max = models.DecimalField(max_digits=12, decimal_places=2, help_text="Upper bound estimate in INR")
    is_estimate_only = models.BooleanField(default=True, help_text="Market estimate only; not a guaranteed purchase offer")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Valuation: {self.year} {self.make_name} {self.model_name} (₹{self.estimated_price_min:,.0f} - ₹{self.estimated_price_max:,.0f})"
