from django import forms
from .models import (
    ServiceBooking, ServiceEnquiry, ServiceCompletionRecord,
    ProviderSchedule, ProviderService, ProviderUnavailableDate, ServiceProvider
)
from garage.models import CustomerVehicle


class ServiceBookingForm(forms.ModelForm):
    customer_vehicle_id = forms.CharField(required=False, widget=forms.HiddenInput())
    custom_vehicle_text = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. 2022 Hyundai Creta SX (O) Diesel - KA-05-MJ-4321'
        })
    )

    class Meta:
        model = ServiceBooking
        fields = [
            'provider', 'service', 'booking_date', 'time_slot',
            'customer_phone', 'customer_address', 'problem_description'
        ]
        widgets = {
            'provider': forms.Select(attrs={'class': 'form-select', 'id': 'booking-provider-select'}),
            'service': forms.Select(attrs={'class': 'form-select', 'id': 'booking-service-select'}),
            'booking_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'id': 'booking-date-input'
            }),
            'time_slot': forms.HiddenInput(attrs={'id': 'booking-slot-input'}),
            'customer_phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '+91 98765 43210'
            }),
            'customer_address': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Your local address / street'
            }),
            'problem_description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Describe symptoms (e.g., squeaking sound on braking, AC not cooling adequately)'
            }),
        }


class ServiceEnquiryForm(forms.ModelForm):
    class Meta:
        model = ServiceEnquiry
        fields = ['name', 'phone', 'email', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Your Full Name'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+91 98765 43210'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'name@example.com'}),
            'message': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Ask about custom quotes, facilities, or parts availability...'}),
        }


class ServiceCompletionForm(forms.ModelForm):
    mark_paid = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}))

    class Meta:
        model = ServiceCompletionRecord
        fields = [
            'labour_charges', 'parts_charges', 'other_charges', 'odometer_reading',
            'work_performed', 'parts_replaced', 'technician_notes',
            'next_service_recommendation_date', 'next_service_recommendation_odometer'
        ]
        widgets = {
            'labour_charges': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'parts_charges': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'other_charges': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'odometer_reading': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'e.g. 45200'}),
            'work_performed': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'List of work executed by technician...'}),
            'parts_replaced': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'e.g. Engine oil (4L), Oil filter, Brake pads (front)'}),
            'technician_notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'Advice for customer on tyre wear or battery life'}),
            'next_service_recommendation_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'next_service_recommendation_odometer': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'e.g. 55000'}),
        }


class ProviderScheduleForm(forms.ModelForm):
    class Meta:
        model = ProviderSchedule
        fields = [
            'weekday', 'is_closed', 'open_time', 'close_time',
            'has_break', 'break_start', 'break_end',
            'slot_duration_minutes', 'max_bookings_per_slot'
        ]
        widgets = {
            'weekday': forms.Select(attrs={'class': 'form-select'}),
            'is_closed': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'open_time': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
            'close_time': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
            'has_break': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'break_start': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
            'break_end': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
            'slot_duration_minutes': forms.NumberInput(attrs={'class': 'form-input', 'min': '15', 'step': '15'}),
            'max_bookings_per_slot': forms.NumberInput(attrs={'class': 'form-input', 'min': '1'}),
        }


class ProviderServiceForm(forms.ModelForm):
    class Meta:
        model = ProviderService
        fields = ['price', 'duration_minutes', 'is_available', 'notes']
        widgets = {
            'price': forms.NumberInput(attrs={'class': 'form-input', 'step': '1.00', 'min': '0'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-input', 'min': '15', 'step': '15'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'notes': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Special workshop notes'}),
        }


class ProviderUnavailableDateForm(forms.ModelForm):
    class Meta:
        model = ProviderUnavailableDate
        fields = ['date', 'reason']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'reason': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Workshop Renovation / Public Holiday'}),
        }

