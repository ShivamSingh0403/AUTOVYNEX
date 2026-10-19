from decimal import Decimal
from datetime import date, timedelta
from django.db import models
from django.contrib.auth.models import User
from vehicles.models import VehicleVariant


class CustomerVehicle(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='garage_vehicles')
    variant = models.ForeignKey(VehicleVariant, on_delete=models.CASCADE, related_name='owned_instances')
    nickname = models.CharField(max_length=100, blank=True, default='', help_text="e.g. My Daily Driver, The Beast")
    registration_number = models.CharField(max_length=20, blank=True, default='', help_text="e.g. KA-01-AB-1234 (Optional)")
    vin_number = models.CharField(max_length=50, blank=True, default='', help_text="17-character VIN / Chassis Number (Private)")
    purchase_year = models.PositiveIntegerField(default=2021)
    current_mileage = models.PositiveIntegerField(default=25000, help_text="Odometer in Kilometers")
    color = models.CharField(max_length=50, blank=True, default='Silver')
    is_default = models.BooleanField(default=False)
    photo = models.ImageField(upload_to='garage_vehicles/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-created_at']

    def save(self, *args, **kwargs):
        if self.is_default:
            # Clear default flag on user's other vehicles
            CustomerVehicle.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    @property
    def display_title(self):
        if self.nickname:
            return f"{self.nickname} ({self.variant.model.make.name} {self.variant.model.name})"
        return f"{self.variant.model.make.name} {self.variant.model.name} {self.variant.name}"

    @property
    def last_service(self):
        return self.maintenance_records.order_by('-service_date').first()

    @property
    def total_expenses(self):
        return self.maintenance_records.aggregate(total=models.Sum('cost'))['total'] or Decimal('0.00')

    @property
    def pending_reminders_count(self):
        return self.reminders.filter(is_completed=False).count()

    @property
    def next_reminder(self):
        return self.reminders.filter(is_completed=False).order_by('due_date', 'due_mileage').first()

    def __str__(self):
        reg = f" [{self.registration_number}]" if self.registration_number else ""
        return f"{self.user.username}'s {self.display_title}{reg}"


class MaintenanceRecord(models.Model):
    SERVICE_TYPES = [
        ('Scheduled Service', 'Scheduled Periodic Maintenance'),
        ('General Servicing', 'General Servicing'),
        ('Engine Oil Change', 'Engine Oil Change'),
        ('Oil & Filter Change', 'Engine Oil & Filter Change'),
        ('Oil Filter Replacement', 'Oil Filter Replacement'),
        ('Air Filter Replacement', 'Air Filter Replacement'),
        ('Brake Inspection', 'Brake Inspection'),
        ('Brake Pad Replacement', 'Brake Pad Replacement'),
        ('Tyre Replacement', 'Tyre Replacement / Rotation'),
        ('Battery Replacement', 'Battery Replacement'),
        ('Coolant Replacement', 'Coolant Replacement'),
        ('Repairs', 'Mechanical & Electrical Repairs'),
        ('Mechanical Repair', 'Mechanical Repair'),
        ('Air Conditioning', 'AC Gas Refill & Filter Clean'),
        ('Accident Repair', 'Bodywork / Denting / Painting'),
        ('Detailing', 'Detailing & Deep Wash'),
        ('Custom', 'Custom Maintenance Activity'),
        ('Other', 'Other Work'),
    ]

    customer_vehicle = models.ForeignKey(CustomerVehicle, on_delete=models.CASCADE, related_name='maintenance_records')
    service_title = models.CharField(max_length=150, blank=True, default='', help_text="e.g. 50,000 KM Major Service")
    service_date = models.DateField()
    mileage = models.PositiveIntegerField(help_text="Odometer reading at time of service (KM)")
    service_type = models.CharField(max_length=50, choices=SERVICE_TYPES, default='Scheduled Service')
    
    # Granular expense breakdown (Decimal arithmetic)
    labour_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text="Labour charges in INR")
    parts_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text="Parts & consumables cost in INR")
    other_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text="Other expenses / taxes in INR")
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text="Total expenditure in INR (calculated on server)")
    
    workshop_name = models.CharField(max_length=150, help_text="Service center, garage, or mechanic name")
    invoice_file = models.FileField(upload_to='invoices/%Y/%m/', blank=True, null=True)
    notes = models.TextField(blank=True, default='', help_text="Work done, parts replaced, next recommendations")
    
    next_service_date = models.DateField(blank=True, null=True, help_text="Recommended next service date")
    next_service_odometer = models.PositiveIntegerField(blank=True, null=True, help_text="Recommended next service odometer reading (KM)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-service_date', '-created_at']

    def save(self, *args, **kwargs):
        # Auto-compute total cost if breakdown is given and cost is zero
        breakdown_sum = (self.labour_cost or Decimal('0.00')) + (self.parts_cost or Decimal('0.00')) + (self.other_cost or Decimal('0.00'))
        if breakdown_sum > 0 and (not self.cost or self.cost == Decimal('0.00')):
            self.cost = breakdown_sum
        elif self.cost > 0 and breakdown_sum == 0:
            # If total cost is provided directly, assign to parts_cost for breakdown consistency
            self.parts_cost = self.cost
        if not self.service_title:
            self.service_title = self.get_service_type_display()
        super().save(*args, **kwargs)

    def __str__(self):
        title = self.service_title or self.service_type
        return f"{self.customer_vehicle.display_title} - {title} on {self.service_date} (₹{self.cost})"


class MaintenanceReminder(models.Model):
    REMINDER_TYPES = [
        ('engine_oil', 'Engine Oil Replacement'),
        ('oil_filter', 'Oil Filter Replacement'),
        ('air_filter', 'Air Filter Replacement'),
        ('brake_pads', 'Brake Pads & Rotors Inspection'),
        ('battery', 'Battery Health Check'),
        ('tyre_inspection', 'Tyre Inspection & Rotation'),
        ('coolant', 'Coolant Replacement'),
        ('general_service', 'Annual Periodic Service'),
        ('insurance', 'Motor Insurance Renewal'),
        ('puc', 'Pollution Under Control (PUC) Certificate'),
        ('registration', 'Vehicle Registration Renewal'),
        ('custom', 'Custom Reminder'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low Priority'),
        ('medium', 'Medium Priority'),
        ('high', 'High Priority'),
        ('urgent', 'Urgent Attention'),
    ]

    customer_vehicle = models.ForeignKey(CustomerVehicle, on_delete=models.CASCADE, related_name='reminders')
    title = models.CharField(max_length=150)
    reminder_type = models.CharField(max_length=40, choices=REMINDER_TYPES, default='general_service')
    due_date = models.DateField(blank=True, null=True)
    due_mileage = models.PositiveIntegerField(blank=True, null=True, help_text="Due at Odometer reading (KM)")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)
    recurrence_months = models.PositiveIntegerField(blank=True, null=True, help_text="Recurring interval in months (e.g. 6 or 12)")
    recurrence_km = models.PositiveIntegerField(blank=True, null=True, help_text="Recurring interval in kilometers (e.g. 10000)")
    notes = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['is_completed', 'due_date', 'due_mileage']

    @property
    def status_state(self):
        if self.is_completed:
            return 'completed'
        today = date.today()
        # Overdue check
        date_overdue = self.due_date and self.due_date < today
        km_overdue = self.due_mileage and (self.customer_vehicle.current_mileage >= self.due_mileage)
        if date_overdue or km_overdue:
            return 'overdue'

        # Due soon check (within 15 days or within 1,000 KM)
        date_due_soon = self.due_date and (self.due_date <= today + timedelta(days=15))
        km_due_soon = self.due_mileage and (0 <= self.due_mileage - self.customer_vehicle.current_mileage <= 1000)
        if date_due_soon or km_due_soon:
            return 'due_soon'

        return 'upcoming'

    def __str__(self):
        return f"{self.title} for {self.customer_vehicle.display_title}"


class VehicleDocument(models.Model):
    DOC_TYPES = [
        ('rc', 'Registration Certificate (RC)'),
        ('insurance', 'Insurance Policy Copy'),
        ('puc', 'PUC Certificate'),
        ('warranty', 'Extended Warranty Card'),
        ('invoice', 'Service / Purchase Invoice'),
        ('other', 'Other Vehicle Document'),
    ]

    customer_vehicle = models.ForeignKey(CustomerVehicle, on_delete=models.CASCADE, related_name='documents')
    doc_type = models.CharField(max_length=30, choices=DOC_TYPES)
    title = models.CharField(max_length=120)
    document_file = models.FileField(upload_to='vehicle_documents/%Y/%m/')
    issue_date = models.DateField(blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True, help_text="Document expiration date")
    notes = models.CharField(max_length=255, blank=True, default='')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    @property
    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date < date.today()
        return False

    @property
    def is_expiring_soon(self):
        if self.expiry_date:
            today = date.today()
            return today <= self.expiry_date <= today + timedelta(days=30)
        return False

    def __str__(self):
        reg = self.customer_vehicle.registration_number or self.customer_vehicle.display_title
        return f"{reg} - {self.title} ({self.get_doc_type_display()})"
