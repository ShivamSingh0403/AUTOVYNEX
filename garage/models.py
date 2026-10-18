from django.db import models
from django.contrib.auth.models import User
from vehicles.models import VehicleVariant


class CustomerVehicle(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='garage_vehicles')
    variant = models.ForeignKey(VehicleVariant, on_delete=models.CASCADE, related_name='owned_instances')
    nickname = models.CharField(max_length=100, blank=True, help_text="e.g. My Daily Driver, The Beast")
    registration_number = models.CharField(max_length=20, help_text="e.g. KA-01-AB-1234")
    vin_number = models.CharField(max_length=50, blank=True, help_text="17-character VIN / Chassis Number (Private)")
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

    def __str__(self):
        return f"{self.user.username}'s {self.display_title} [{self.registration_number}]"


class MaintenanceRecord(models.Model):
    SERVICE_TYPES = [
        ('Scheduled Service', 'Scheduled Periodic Maintenance'),
        ('Oil & Filter Change', 'Engine Oil & Filter Change'),
        ('Brake Service', 'Brake Pad / Disc Replacement'),
        ('Tyre Service', 'Tyre Rotation / Wheel Alignment / New Tyres'),
        ('Battery Replacement', 'Battery Replacement'),
        ('Air Conditioning', 'AC Gas Refill & Filter Clean'),
        ('Accident Repair', 'Bodywork / Denting / Painting'),
        ('Mechanical Repair', 'Suspension / Clutch / Transmission'),
        ('Detailing', 'Deep Wash, Ceramic / Teflon Coating'),
        ('Other', 'Other Mechanical Work'),
    ]

    customer_vehicle = models.ForeignKey(CustomerVehicle, on_delete=models.CASCADE, related_name='maintenance_records')
    service_date = models.DateField()
    mileage = models.PositiveIntegerField(help_text="Odometer reading at time of service")
    service_type = models.CharField(max_length=50, choices=SERVICE_TYPES, default='Scheduled Service')
    cost = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total expenditure in INR")
    workshop_name = models.CharField(max_length=150, help_text="Service center or garage name")
    invoice_file = models.FileField(upload_to='invoices/', blank=True, null=True)
    notes = models.TextField(blank=True, help_text="Work done, parts replaced, next recommendations")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-service_date', '-created_at']

    def __str__(self):
        return f"{self.customer_vehicle.display_title} - {self.service_type} on {self.service_date} (₹{self.cost})"


class MaintenanceReminder(models.Model):
    REMINDER_TYPES = [
        ('engine_oil', 'Engine Oil Replacement'),
        ('brake_pads', 'Brake Pads Inspection'),
        ('battery', 'Battery Health Check'),
        ('tyre_rotation', 'Tyre Rotation & Alignment'),
        ('general_service', 'Annual Periodic Service'),
        ('insurance', 'Motor Insurance Renewal'),
        ('puc', 'Pollution Under Control (PUC) Certificate'),
    ]

    customer_vehicle = models.ForeignKey(CustomerVehicle, on_delete=models.CASCADE, related_name='reminders')
    title = models.CharField(max_length=150)
    reminder_type = models.CharField(max_length=40, choices=REMINDER_TYPES, default='general_service')
    due_date = models.DateField(blank=True, null=True)
    due_mileage = models.PositiveIntegerField(blank=True, null=True, help_text="Due at Odometer reading (KM)")
    is_completed = models.BooleanField(default=False)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['is_completed', 'due_date']

    def __str__(self):
        return f"{self.title} for {self.customer_vehicle.display_title}"


class VehicleDocument(models.Model):
    DOC_TYPES = [
        ('rc', 'Registration Certificate (RC)'),
        ('insurance', 'Insurance Policy Copy'),
        ('puc', 'PUC Certificate'),
        ('warranty', 'Extended Warranty Card'),
        ('invoice', 'Original Purchase Invoice'),
        ('other', 'Other Document'),
    ]

    customer_vehicle = models.ForeignKey(CustomerVehicle, on_delete=models.CASCADE, related_name='documents')
    doc_type = models.CharField(max_length=30, choices=DOC_TYPES)
    title = models.CharField(max_length=120)
    document_file = models.FileField(upload_to='vehicle_documents/')
    expiry_date = models.DateField(blank=True, null=True, help_text="Document expiration date (e.g. for Insurance/PUC)")
    notes = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.customer_vehicle.registration_number} - {self.title} ({self.get_doc_type_display()})"
