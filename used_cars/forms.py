from django import forms
from .models import UsedCarListing, UsedCarImage, UsedCarEnquiry, UsedCarReport


class MultipleFileInput(forms.FileInput):
    def __init__(self, attrs=None):
        super().__init__(attrs)
        self.attrs['multiple'] = True


class UsedCarListingForm(forms.ModelForm):
    gallery_images = forms.FileField(
        required=False,
        widget=MultipleFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        help_text="Upload additional exterior, interior, or mechanical photographs (Max 5MB each)"
    )

    class Meta:
        model = UsedCarListing
        fields = [
            'title', 'make_name', 'model_name', 'variant_name',
            'year', 'registration_year', 'mileage', 'fuel_type',
            'transmission', 'owners_count', 'condition', 'expected_price',
            'location_city', 'location_state', 'location_area',
            'registration_state', 'insurance_valid_till', 'description',
            'primary_image', 'allow_phone_contact', 'contact_phone'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 2021 Hyundai Creta SX(O) 1.5 AT'}),
            'make_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Hyundai'}),
            'model_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Creta'}),
            'variant_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. SX(O) AT'}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'min': 1995, 'max': 2026}),
            'registration_year': forms.NumberInput(attrs={'class': 'form-control', 'min': 1995, 'max': 2026}),
            'mileage': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 35000', 'min': 0}),
            'fuel_type': forms.Select(attrs={'class': 'form-select'}),
            'transmission': forms.Select(attrs={'class': 'form-select'}),
            'owners_count': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
            'condition': forms.Select(attrs={'class': 'form-select'}),
            'expected_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 1450000', 'min': 10000}),
            'location_city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Bengaluru'}),
            'location_state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Karnataka'}),
            'location_area': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Indiranagar'}),
            'registration_state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Karnataka (KA)'}),
            'insurance_valid_till': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Provide honest information regarding vehicle maintenance history, condition, accessories, and reason for selling...'}),
            'primary_image': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'allow_phone_contact': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. +91 98765 43210'}),
        }

    def clean_expected_price(self):
        price = self.cleaned_data.get('expected_price')
        if price is not None and price <= 0:
            raise forms.ValidationError("Asking price must be greater than zero.")
        return price

    def clean_year(self):
        year = self.cleaned_data.get('year')
        if year is not None and (year < 1990 or year > 2026):
            raise forms.ValidationError("Manufacturing year must be between 1990 and 2026.")
        return year

    def clean_mileage(self):
        mileage = self.cleaned_data.get('mileage')
        if mileage is not None and mileage < 0:
            raise forms.ValidationError("Kilometres driven cannot be negative.")
        return mileage


    def clean_primary_image(self):
        image = self.cleaned_data.get('primary_image')
        if image:
            if image.size > 8 * 1024 * 1024:
                raise forms.ValidationError("Primary image file size cannot exceed 8 MB.")
            ext = image.name.split('.')[-1].lower()
            if ext not in ['jpg', 'jpeg', 'png', 'webp']:
                raise forms.ValidationError("Only JPG, JPEG, PNG, or WEBP images are supported.")
        return image


class UsedCarEnquiryForm(forms.ModelForm):
    class Meta:
        model = UsedCarEnquiry
        fields = ['sender_name', 'sender_email', 'sender_phone', 'enquiry_type', 'offer_amount', 'message']
        widgets = {
            'sender_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Full Name', 'required': True}),
            'sender_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Your Email Address', 'required': True}),
            'sender_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your 10-Digit Mobile Number', 'required': True}),
            'enquiry_type': forms.Select(attrs={'class': 'form-select'}),
            'offer_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Your Offer in INR (Optional)', 'min': 1000}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Specify your questions or queries regarding vehicle history, physical viewing, or terms...', 'required': True}),
        }

    def clean_sender_phone(self):
        phone = self.cleaned_data.get('sender_phone', '').strip()
        digits = [c for c in phone if c.isdigit()]
        if len(digits) < 10:
            raise forms.ValidationError("Please enter a valid phone number with at least 10 digits.")
        return phone


class UsedCarReportForm(forms.ModelForm):
    class Meta:
        model = UsedCarReport
        fields = ['reason', 'details', 'reporter_name', 'reporter_email']
        widgets = {
            'reason': forms.Select(attrs={'class': 'form-select'}),
            'details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Explain why this listing violates guidelines...', 'required': True}),
            'reporter_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Name (Optional)'}),
            'reporter_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Your Email (Optional)'}),
        }
