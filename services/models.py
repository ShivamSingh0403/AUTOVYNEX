from decimal import Decimal
import datetime
import urllib.parse
import uuid

from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify


class ServiceCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    icon_name = models.CharField(max_length=50, default='wrench', help_text="Lucide icon identifier")
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Service Categories'
        ordering = ['sort_order', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ServiceProvider(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active & Accepting Bookings'),
        ('pending', 'Pending Approval'),
        ('inactive', 'Inactive / Temporarily Closed'),
    ]

    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='owned_service_providers')
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    description = models.TextField(blank=True, default='')
    logo = models.ImageField(upload_to='providers/logos/', blank=True, null=True)
    cover_image = models.ImageField(upload_to='providers/covers/', blank=True, null=True)
    image = models.ImageField(upload_to='providers/', blank=True, null=True)  # legacy compatibility
    
    address = models.TextField()
    city = models.CharField(max_length=100, default='Bengaluru')
    state = models.CharField(max_length=100, default='Karnataka', blank=True)
    postal_code = models.CharField(max_length=20, default='560001', blank=True)
    
    contact_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    operating_hours = models.CharField(max_length=100, default='Mon - Sat: 9:00 AM - 7:00 PM')
    
    supported_brands = models.ManyToManyField('vehicles.VehicleMake', blank=True, related_name='service_providers')
    facilities = models.TextField(blank=True, default='Customer Lounge, Wi-Fi, Card / UPI Payment, Express Service Bay, Pick & Drop Available')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_verified = models.BooleanField(default=False, help_text="Verified real business credentials check")
    verified = models.BooleanField(default=False)  # legacy field
    is_demo = models.BooleanField(default=True, help_text="Distinguishes demo sample providers from independently verified real businesses")
    
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.8)
    total_reviews = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.name}-{self.city}")
            unique_slug = base_slug
            counter = 1
            while ServiceProvider.objects.filter(slug=unique_slug).exclude(pk=self.pk).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = unique_slug
        # Keep verified and is_verified synchronized
        if self.is_verified and not self.verified:
            self.verified = True
        super().save(*args, **kwargs)

    @property
    def external_map_url(self):
        query_parts = [self.name, self.address, self.city, self.postal_code]
        query_string = ", ".join([p for p in query_parts if p])
        return f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote_plus(query_string)}"

    @property
    def facilities_list(self):
        if not self.facilities:
            return []
        return [f.strip() for f in self.facilities.split(',') if f.strip()]

    def __str__(self):
        badge = " [DEMO]" if self.is_demo else " [VERIFIED]"
        return f"{self.name} ({self.city}){badge}"


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
        ('electrical', 'Electrical Repair & Diagnostics'),
        ('bodywork', 'Denting and Painting'),
        ('emergency', 'Emergency Roadside Support'),
        ('other', 'Specialized Auto Service'),
    ]

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    category = models.CharField(max_length=30, choices=CATEGORIES, default='general')
    category_ref = models.ForeignKey(ServiceCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='services')
    estimated_duration = models.CharField(max_length=60, default='2 - 3 hours')
    estimated_duration_minutes = models.PositiveIntegerField(default=120, help_text="Typical duration in minutes")
    starting_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text="Configured baseline starting price in INR")
    supported_vehicle_types = models.CharField(max_length=150, default='Hatchback, Sedan, SUV, EV', blank=True)
    description = models.TextField()
    icon_name = models.CharField(max_length=50, default='wrench', help_text="Lucide icon identifier")
    is_popular = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            unique_slug = base_slug
            counter = 1
            while Service.objects.filter(slug=unique_slug).exclude(pk=self.pk).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = unique_slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} (from ₹{self.starting_price:,.2f})"


class ProviderService(models.Model):
    """Specific service offered by a provider with workshop-configured price and duration."""
    provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE, related_name='provider_services')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='provider_offerings')
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Workshop-configured service price in INR")
    duration_minutes = models.PositiveIntegerField(default=120, help_text="Estimated duration in minutes for this workshop")
    is_available = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default='')

    class Meta:
        unique_together = ('provider', 'service')
        ordering = ['service__name']

    def __str__(self):
        return f"{self.provider.name} - {self.service.name}: ₹{self.price:,.2f}"


class ProviderSchedule(models.Model):
    """Weekly operating schedule for a service provider."""
    WEEKDAYS = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE, related_name='schedules')
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAYS)
    is_closed = models.BooleanField(default=False)
    open_time = models.TimeField(default=datetime.time(9, 0))
    close_time = models.TimeField(default=datetime.time(18, 0))
    has_break = models.BooleanField(default=True)
    break_start = models.TimeField(default=datetime.time(13, 0), null=True, blank=True)
    break_end = models.TimeField(default=datetime.time(14, 0), null=True, blank=True)
    slot_duration_minutes = models.PositiveIntegerField(default=60)
    max_bookings_per_slot = models.PositiveIntegerField(default=2, help_text="Concurrent vehicles / bays capacity")

    class Meta:
        unique_together = ('provider', 'weekday')
        ordering = ['weekday']

    def __str__(self):
        day_str = dict(self.WEEKDAYS).get(self.weekday, 'Day')
        if self.is_closed:
            return f"{self.provider.name} - {day_str}: Closed"
        return f"{self.provider.name} - {day_str}: {self.open_time.strftime('%I:%M %p')} - {self.close_time.strftime('%I:%M %p')}"


class ProviderUnavailableDate(models.Model):
    """Specific holiday, off-day, or workshop maintenance closure."""
    provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE, related_name='unavailable_dates')
    date = models.DateField()
    reason = models.CharField(max_length=200, default='Holiday / Workshop Closure')

    class Meta:
        unique_together = ('provider', 'date')
        ordering = ['date']

    def __str__(self):
        return f"{self.provider.name} - {self.date} ({self.reason})"


class ServiceBooking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
        ('rescheduled', 'Rescheduled'),
        ('in_progress', 'Vehicle In Service'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Unpaid (Pay at Workshop)'),
        ('paid_at_workshop', 'Paid at Workshop'),
        ('paid_online_demo', 'Paid Online (Demo)'),
        ('refunded', 'Refunded'),
    ]

    TIME_SLOTS = [
        ('09:00 - 10:00 AM', '09:00 AM - 10:00 AM'),
        ('10:00 - 11:00 AM', '10:00 AM - 11:00 AM'),
        ('11:00 - 12:00 PM', '11:00 AM - 12:00 PM'),
        ('12:00 - 01:00 PM', '12:00 PM - 01:00 PM'),
        ('02:00 - 03:00 PM', '02:00 PM - 03:00 PM'),
        ('03:00 - 04:00 PM', '03:00 PM - 04:00 PM'),
        ('04:00 - 05:00 PM', '04:00 PM - 05:00 PM'),
        ('05:00 - 06:00 PM', '05:00 PM - 06:00 PM'),
    ]

    booking_number = models.CharField(max_length=32, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='service_bookings')
    provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE, related_name='bookings')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='bookings')
    provider_service = models.ForeignKey(ProviderService, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    
    customer_vehicle = models.ForeignKey('garage.CustomerVehicle', on_delete=models.SET_NULL, null=True, blank=True, related_name='service_bookings')
    vehicle_info = models.CharField(max_length=200, help_text="Car Make Model Variant Reg")
    
    booking_date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    time_slot = models.CharField(max_length=60)
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=30, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    
    customer_address = models.TextField(help_text="Pickup or customer address", blank=True, default='')
    customer_phone = models.CharField(max_length=20)
    problem_description = models.TextField(blank=True, help_text="Specific issues or notes observed")
    
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    price_estimate_snapshot = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text="Snapshot of price at booking time")
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Actual bill upon service completion")
    
    cancellation_reason = models.TextField(blank=True, default='')
    rescheduled_from = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='rescheduled_to')
    
    is_simulated = models.BooleanField(default=True, help_text="Simulated for academic/demonstration purposes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-booking_date', '-created_at']

    def save(self, *args, **kwargs):
        if not self.booking_number:
            self.booking_number = f"AVX-SRV-{uuid.uuid4().hex[:8].upper()}"
        if not self.price_estimate_snapshot and self.estimated_cost:
            self.price_estimate_snapshot = self.estimated_cost
        super().save(*args, **kwargs)

    @property
    def can_be_cancelled(self):
        """Customers can cancel if appointment is pending, confirmed, or rescheduled (before in_progress/completed/rejected)."""
        return self.status in ['pending', 'confirmed', 'rescheduled']

    @property
    def can_be_rescheduled(self):
        """Customers can request reschedule if appointment is not yet in progress, completed, or cancelled."""
        return self.status in ['pending', 'confirmed', 'rescheduled']

    def __str__(self):
        return f"{self.booking_number} - {self.service.name} ({self.booking_date} {self.time_slot})"


class ServiceBookingHistory(models.Model):
    """Audit trail recording every status change."""
    booking = models.ForeignKey(ServiceBooking, on_delete=models.CASCADE, related_name='history_logs')
    previous_status = models.CharField(max_length=30, blank=True, default='')
    new_status = models.CharField(max_length=30)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    customer_note = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.booking.booking_number}: {self.previous_status} -> {self.new_status} at {self.created_at}"


class ServiceCompletionRecord(models.Model):
    """Workshop completion details with breakdown of labour, parts, and odometer."""
    booking = models.OneToOneField(ServiceBooking, on_delete=models.CASCADE, related_name='completion_record')
    work_performed = models.TextField(help_text="Detailed summary of work carried out")
    parts_replaced = models.TextField(blank=True, default='', help_text="List of parts or consumables replaced")
    
    labour_charges = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    parts_charges = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    other_charges = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    odometer_reading = models.PositiveIntegerField(null=True, blank=True, help_text="Odometer reading in KM at completion")
    technician_notes = models.TextField(blank=True, default='', help_text="Observations & advice")
    
    next_service_recommendation_date = models.DateField(null=True, blank=True)
    next_service_recommendation_odometer = models.PositiveIntegerField(null=True, blank=True)
    
    linked_maintenance_record = models.ForeignKey(
        'garage.MaintenanceRecord',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_booking_completions'
    )
    completed_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        calculated_total = (self.labour_charges or Decimal('0.00')) + (self.parts_charges or Decimal('0.00')) + (self.other_charges or Decimal('0.00'))
        if calculated_total > 0 and (not self.final_amount or self.final_amount == Decimal('0.00')):
            self.final_amount = calculated_total
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Completion for {self.booking.booking_number} - Total ₹{self.final_amount:,.2f}"


class ServiceEnquiry(models.Model):
    """Contact / enquiry message for a specific service provider."""
    provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE, related_name='enquiries')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    message = models.TextField()
    is_responded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Enquiry from {self.name} for {self.provider.name}"


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
    estimated_fee = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('500.00'))
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
