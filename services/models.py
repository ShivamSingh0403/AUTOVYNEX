from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
import uuid


class ServiceProvider(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    city = models.CharField(max_length=100, default='Bengaluru')
    address = models.TextField()
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.8)
    total_reviews = models.PositiveIntegerField(default=124)
    contact_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    verified = models.BooleanField(default=True)
    image = models.ImageField(upload_to='providers/', blank=True, null=True)
    operating_hours = models.CharField(max_length=100, default='Mon - Sat: 9:00 AM - 7:00 PM')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-rating', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.name}-{self.city}")
        super().save(*args, **kwargs)

class ServiceCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    icon_name = models.CharField(max_length=50, default='wrench', help_text="Lucide icon identifier")
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = 'Service Categories'
        ordering = ['sort_order', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Service(models.Model):
    CATEGORIES = [
        ('general', 'General Periodic Servicing'),
        ('oil', 'Oil & Filter Replacement'),
        ('brakes', 'Brake Inspection & Overhaul'),
        ('battery', 'Battery Diagnostics & Replacement'),
        ('ac', 'Air Conditioning Service & Gas'),
        ('washing', 'Premium Washing & Detailing'),
        ('tyre', 'Tyres, Alignment & Balancing'),
        ('mechanical', 'Suspension & Mechanical Repairs'),
    ]

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    category = models.CharField(max_length=30, choices=CATEGORIES, default='general')
    estimated_duration = models.CharField(max_length=60, default='2 - 3 hours')
    starting_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Starting price in INR")
    description = models.TextField()
    icon_name = models.CharField(max_length=50, default='wrench', help_text="Lucide icon identifier")
    is_popular = models.BooleanField(default=False)

    class Meta:
        ordering = ['category', 'starting_price']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} (from ₹{self.starting_price})"


class ServiceBooking(models.Model):
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('in_progress', 'Vehicle In Service'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    TIME_SLOTS = [
        ('09:00 - 11:00 AM', '09:00 AM - 11:00 AM (Morning)'),
        ('11:00 AM - 01:00 PM', '11:00 AM - 01:00 PM (Mid-day)'),
        ('02:00 - 04:00 PM', '02:00 PM - 04:00 PM (Afternoon)'),
        ('04:00 - 06:00 PM', '04:00 PM - 06:00 PM (Evening)'),
    ]

    booking_number = models.CharField(max_length=32, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='service_bookings')
    provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE, related_name='bookings')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='bookings')
    vehicle_info = models.CharField(max_length=200, help_text="Car Make Model Variant Reg")
    booking_date = models.DateField()
    time_slot = models.CharField(max_length=40, choices=TIME_SLOTS)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='confirmed')
    customer_address = models.TextField(help_text="Pickup or service address")
    customer_phone = models.CharField(max_length=20)
    problem_description = models.TextField(blank=True, help_text="Specific issues observed")
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_simulated = models.BooleanField(default=True, help_text="Simulated for academic/demonstration purposes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-booking_date', '-created_at']
        unique_together = ('provider', 'booking_date', 'time_slot')

    def save(self, *args, **kwargs):
        if not self.booking_number:
            self.booking_number = f"AVX-SRV-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.booking_number} - {self.service.name} ({self.booking_date} {self.time_slot})"


class InstallationRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Scheduling'),
        ('scheduled', 'Appointment Scheduled'),
        ('completed', 'Installation Completed'),
        ('cancelled', 'Cancelled'),
    ]

    request_number = models.CharField(max_length=32, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='installation_requests')
    product_name = models.CharField(max_length=200)
    service_provider = models.ForeignKey(ServiceProvider, on_delete=models.SET_NULL, null=True, blank=True)
    vehicle_info = models.CharField(max_length=200)
    preferred_date = models.DateField(blank=True, null=True)
    preferred_slot = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    estimated_fee = models.DecimalField(max_digits=8, decimal_places=2, default=500.00)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.request_number:
            self.request_number = f"AVX-INS-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.request_number}: {self.product_name} ({self.status})"
