from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import MissingPartEnquiry
from garage.models import CustomerVehicle


def missing_part_request(request):
    customer_vehicles = []
    if request.user.is_authenticated:
        customer_vehicles = CustomerVehicle.objects.filter(user=request.user)

    if request.method == 'POST':
        part_name = request.POST.get('part_name', '').strip()
        vehicle_details = request.POST.get('vehicle_details', '').strip()
        category = request.POST.get('category', 'Mechanical / Engine')
        part_number = request.POST.get('part_number', '').strip()
        vin_chassis = request.POST.get('vin_chassis', '').strip()
        description = request.POST.get('description', '').strip()
        contact_name = request.POST.get('contact_name', '').strip()
        contact_email = request.POST.get('contact_email', '').strip()
        contact_phone = request.POST.get('contact_phone', '').strip()
        contact_pref = request.POST.get('contact_preference', 'whatsapp')
        image = request.FILES.get('sample_photo')
        # File validation
        if image:
            if image.size > 5 * 1024 * 1024:
                messages.error(request, "Image file size exceeds the 5MB limit.")
                return redirect('enquiries:missing_part_request')
            ext = image.name.split('.')[-1].lower()
            if ext not in ['jpg', 'jpeg', 'png', 'webp']:
                messages.error(request, "Invalid image format. Supported formats: JPG, PNG, WEBP.")
                return redirect('enquiries:missing_part_request')

        enquiry = MissingPartEnquiry.objects.create(
            user=request.user if request.user.is_authenticated else None,
            part_name=part_name,
            vehicle_details=vehicle_details,
            category=category,
            part_number=part_number,
            vin_chassis=vin_chassis,
            description=description,
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            contact_preference=contact_pref,
            damaged_part_image=image,
            status='submitted'
        )

        from .models import EnquiryStatusHistory
        EnquiryStatusHistory.objects.create(
            enquiry=enquiry,
            status='submitted',
            notes='Enquiry created and assigned to logistics sourcing queue.',
            changed_by=request.user if request.user.is_authenticated else None
        )

        messages.success(request, f"Your missing part enquiry has been dispatched to logistics! Reference: {enquiry.reference_code}")
        return redirect('enquiries:enquiry_status', reference_code=enquiry.reference_code)

    return render(request, 'enquiries/missing_part_form.html', {'customer_vehicles': customer_vehicles})


def enquiry_status(request, reference_code):
    enquiry = get_object_or_404(MissingPartEnquiry, reference_code=reference_code)
    return render(request, 'enquiries/enquiry_status.html', {'enquiry': enquiry})
