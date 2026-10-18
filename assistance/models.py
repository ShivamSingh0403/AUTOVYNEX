from django.db import models
from django.contrib.auth.models import User
import uuid


class RoadsideAssistanceRequest(models.Model):
    REQUEST_TYPES = [
        ('breakdown', 'Mechanical Breakdown / Engine Failure'),
        ('flat_tyre', 'Punctured / Flat Tyre Assistance'),
        ('battery', 'Dead Battery / Jump Start Required'),
        ('towing', 'Hydraulic Flatbed Towing Required'),
        ('fuel_delivery', 'Emergency Fuel / EV Quick Charge'),
        ('emergency', 'Accident / Lockout / Other Urgent Emergency'),
    ]

    URGENCY_LEVELS = [
        ('critical', 'Critical (Stranded on Highway/Dangerous Spot)'),
        ('urgent', 'Urgent (Stranded in City)'),
        ('normal', 'Normal (Parked safely at home/office)'),
    ]

    STATUS_CHOICES = [
        ('received', 'Ticket Logged & Received'),
        ('assigned', 'Assistance Unit Assigned'),
        ('dispatched', 'Patrol Vehicle Dispatched'),
        ('resolved', 'Assistance Provided & Closed'),
        ('cancelled', 'Cancelled by User'),
    ]

    ticket_number = models.CharField(max_length=32, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assistance_requests')
    
    contact_name = models.CharField(max_length=120)
    contact_phone = models.CharField(max_length=20)
    request_type = models.CharField(max_length=30, choices=REQUEST_TYPES, default='breakdown')
    urgency = models.CharField(max_length=20, choices=URGENCY_LEVELS, default='urgent')
    
    vehicle_details = models.CharField(max_length=200, help_text="Car Model & Registration number")
    location_address = models.TextField(help_text="Current location, landmark, or GPS description")
    city = models.CharField(max_length=80, default='Bengaluru')
    landmark = models.CharField(max_length=150, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    description = models.TextField(help_text="Symptoms or situation details")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='received')
    assigned_patrol = models.CharField(max_length=120, blank=True, default='AUTOVYNEX Rapid Response Unit #4')
    estimated_arrival_minutes = models.PositiveIntegerField(default=25)
    admin_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            self.ticket_number = f"AVX-RSA-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket_number} - {self.get_request_type_display()} ({self.status})"
