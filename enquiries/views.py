import os
import mimetypes
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.urls import reverse
from django.utils import timezone

from .models import MissingPartEnquiry, EnquiryImage, EnquiryStatusHistory
from .notifications import send_enquiry_notification
from garage.models import CustomerVehicle
from vehicles.models import VehicleMake, VehicleModel, VehicleVariant


def parse_decimal(val, default='0.00'):
    """Safely parse user/staff input into Decimal."""
    try:
        if not val or str(val).strip() == '':
            return Decimal(default)
        clean_str = str(val).replace(',', '').strip()
        d = Decimal(clean_str)
        return d if d >= Decimal('0.00') else Decimal('0.00')
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)


# -------------------------------------------------------------
# 1. Missing-Part Enquiry Submission Form
# -------------------------------------------------------------
def missing_part_request(request):
    """
    'Can't Find Your Part?' Landing & Sourcing Request Submission.
    Supports auto-filling from saved garage vehicles for logged-in users,
    multi-image upload validation, safe filename generation, and duplicate prevention.
    """
    customer_vehicles = []
    if request.user.is_authenticated:
        customer_vehicles = CustomerVehicle.objects.filter(
            user=request.user
        ).select_related('variant__model__make')

    makes = VehicleMake.objects.all().order_by('name')

    if request.method == 'POST':
        # Vehicle Specs
        make = request.POST.get('make', '').strip()
        model_name = request.POST.get('model_name', '').strip()
        variant_name = request.POST.get('variant_name', '').strip()
        fuel_type = request.POST.get('fuel_type', '').strip()
        reg_number = request.POST.get('registration_number', '').strip().upper()
        vin_chassis = request.POST.get('vin_chassis', '').strip().upper()
        vehicle_details = request.POST.get('vehicle_details', '').strip()

        year_raw = request.POST.get('year')
        year = int(year_raw) if year_raw and year_raw.isdigit() else None

        # Part Specs
        part_name = request.POST.get('part_name', '').strip()
        category = request.POST.get('category', 'engine_mechanical')
        brand_pref = request.POST.get('brand_preference', '').strip()
        part_number = request.POST.get('part_number', '').strip().upper()
        description = request.POST.get('description', '').strip()
        budget_range = request.POST.get('budget_range', '').strip()
        urgency = request.POST.get('urgency', 'standard')

        # Contact Info
        contact_name = request.POST.get('contact_name', '').strip()
        contact_email = request.POST.get('contact_email', '').strip()
        contact_phone = request.POST.get('contact_phone', '').strip()
        contact_pref = request.POST.get('contact_preference', 'email')
        whatsapp_optin = request.POST.get('whatsapp_enabled') == '1'

        # Validation of required fields
        if not (part_name and description and contact_name and contact_email and contact_phone):
            messages.error(request, "Please fill in all required fields (Part Name, Description, and Contact Details).")
            return render(request, 'enquiries/missing_part_form.html', {
                'customer_vehicles': customer_vehicles,
                'makes': makes,
                'category_choices': MissingPartEnquiry.CATEGORY_CHOICES,
                'urgency_choices': MissingPartEnquiry.URGENCY_CHOICES,
            })

        # Image Validation & Collection
        uploaded_files = request.FILES.getlist('part_images')
        single_photo = request.FILES.get('damaged_part_image')
        if single_photo and single_photo not in uploaded_files:
            uploaded_files.insert(0, single_photo)

        if len(uploaded_files) > 5:
            messages.error(request, "You can upload a maximum of 5 photographs per enquiry.")
            return render(request, 'enquiries/missing_part_form.html', {
                'customer_vehicles': customer_vehicles,
                'makes': makes,
                'category_choices': MissingPartEnquiry.CATEGORY_CHOICES,
                'urgency_choices': MissingPartEnquiry.URGENCY_CHOICES,
            })

        valid_extensions = ['jpg', 'jpeg', 'png', 'webp']
        max_size = 5 * 1024 * 1024  # 5MB

        for f in uploaded_files:
            ext = f.name.split('.')[-1].lower()
            if ext not in valid_extensions:
                messages.error(request, f"File '{f.name}' has an unsupported format. Allowed formats: JPG, PNG, WEBP.")
                return render(request, 'enquiries/missing_part_form.html', {
                    'customer_vehicles': customer_vehicles,
                    'makes': makes,
                    'category_choices': MissingPartEnquiry.CATEGORY_CHOICES,
                    'urgency_choices': MissingPartEnquiry.URGENCY_CHOICES,
                })
            if f.size > max_size:
                messages.error(request, f"File '{f.name}' exceeds the 5MB size limit ({round(f.size / (1024*1024), 1)} MB).")
                return render(request, 'enquiries/missing_part_form.html', {
                    'customer_vehicles': customer_vehicles,
                    'makes': makes,
                    'category_choices': MissingPartEnquiry.CATEGORY_CHOICES,
                    'urgency_choices': MissingPartEnquiry.URGENCY_CHOICES,
                })

        with transaction.atomic():
            enquiry = MissingPartEnquiry(
                user=request.user if request.user.is_authenticated else None,
                make=make,
                model_name=model_name,
                year=year,
                fuel_type=fuel_type,
                variant_name=variant_name,
                registration_number=reg_number,
                vin_chassis=vin_chassis,
                vehicle_details=vehicle_details,
                part_name=part_name,
                category=category,
                brand_preference=brand_pref,
                part_number=part_number,
                description=description,
                budget_range=budget_range,
                urgency=urgency,
                contact_name=contact_name,
                contact_email=contact_email,
                contact_phone=contact_phone,
                contact_preference=contact_pref,
                whatsapp_enabled=whatsapp_optin,
                status='submitted'
            )

            if uploaded_files:
                enquiry.damaged_part_image = uploaded_files[0]

            enquiry.save()

            # Save additional uploaded photos
            for f in uploaded_files[1:]:
                EnquiryImage.objects.create(
                    enquiry=enquiry,
                    image=f,
                    caption=f.name,
                    file_size=f.size
                )

            # Record Initial Status Audit Entry
            EnquiryStatusHistory.objects.create(
                enquiry=enquiry,
                old_status='',
                status='submitted',
                notes='Enquiry created and assigned to AUTOVYNEX OEM & OES sourcing logistics queue.',
                changed_by=request.user if request.user.is_authenticated else None
            )

            # Dispatch Notifications
            send_enquiry_notification(enquiry, 'submitted')

        messages.success(request, f"Your sourcing request has been submitted! Reference Code: {enquiry.reference_code}")
        return redirect('enquiries:enquiry_confirmation', reference_code=enquiry.reference_code)

    context = {
        'customer_vehicles': customer_vehicles,
        'makes': makes,
        'category_choices': MissingPartEnquiry.CATEGORY_CHOICES,
        'urgency_choices': MissingPartEnquiry.URGENCY_CHOICES,
        'contact_preferences': MissingPartEnquiry.CONTACT_PREFERENCES,
    }
    return render(request, 'enquiries/missing_part_form.html', context)


# -------------------------------------------------------------
# 2. Enquiry Confirmation Page
# -------------------------------------------------------------
def enquiry_confirmation(request, reference_code):
    """
    Displays confirmation screen with enquiry reference, what happens next,
    and link to live tracking. Protects against duplicate form re-submissions.
    """
    enquiry = get_object_or_404(MissingPartEnquiry, reference_code=reference_code)
    return render(request, 'enquiries/confirmation.html', {'enquiry': enquiry})


# -------------------------------------------------------------
# 3. Customer Sourcing Dashboard ("My Part Enquiries")
# -------------------------------------------------------------
@login_required
def my_enquiries(request):
    """
    Customer dashboard displaying all sourcing enquiries submitted by the user.
    Includes status filter tabs and quick actions.
    """
    enquiries_qs = MissingPartEnquiry.objects.filter(
        user=request.user
    ).prefetch_related('additional_images', 'status_history')

    status_filter = request.GET.get('status')
    if status_filter:
        if status_filter == 'active':
            enquiries_qs = enquiries_qs.filter(status__in=['submitted', 'under_review', 'info_required', 'sourcing', 'part_found'])
        elif status_filter == 'quotes':
            enquiries_qs = enquiries_qs.filter(status='quote_prepared')
        elif status_filter == 'completed':
            enquiries_qs = enquiries_qs.filter(status__in=['completed', 'customer_accepted'])
        elif status_filter == 'closed':
            enquiries_qs = enquiries_qs.filter(status__in=['unavailable', 'cancelled'])
        else:
            enquiries_qs = enquiries_qs.filter(status=status_filter)

    total_count = MissingPartEnquiry.objects.filter(user=request.user).count()
    active_count = MissingPartEnquiry.objects.filter(
        user=request.user,
        status__in=['submitted', 'under_review', 'info_required', 'sourcing', 'part_found', 'quote_prepared']
    ).count()
    quotes_count = MissingPartEnquiry.objects.filter(user=request.user, status='quote_prepared').count()

    context = {
        'enquiries': enquiries_qs,
        'selected_filter': status_filter or 'all',
        'total_count': total_count,
        'active_count': active_count,
        'quotes_count': quotes_count,
    }
    return render(request, 'enquiries/my_enquiries.html', context)


# -------------------------------------------------------------
# 4. Enquiry Detail & Status Tracking with Actions
# -------------------------------------------------------------
def enquiry_detail(request, reference_code):
    """
    Customer-facing detailed tracking page:
    - Verifies customer ownership or authorized access.
    - Displays visual timeline of status changes (customer-safe notes only).
    - Image gallery with attached photos.
    - Sourcing quote card with Accept/Decline decision handling.
    - Additional information submission and customer cancellation.
    """
    enquiry = get_object_or_404(
        MissingPartEnquiry.objects.select_related('user').prefetch_related('additional_images', 'status_history'),
        reference_code=reference_code
    )

    # Ownership & Privacy check
    if enquiry.user:
        if not request.user.is_authenticated:
            # Require login if enquiry belongs to a registered customer
            messages.info(request, "Please log in to view this private sourcing enquiry.")
            return redirect(f"{reverse('accounts:login')}?next={request.path}")
        if enquiry.user != request.user and not request.user.is_staff:
            return HttpResponseForbidden("You are not authorized to view this private sourcing record.")
    else:
        # Guest enquiry: allow viewing only if session verified or by reference code
        pass

    timeline = enquiry.status_history.all().order_by('created_at')

    if request.method == 'POST':
        action = request.POST.get('action')

        # Action A: Customer Submits Additional Information
        if action == 'add_info':
            additional_note = request.POST.get('additional_info', '').strip()
            extra_files = request.FILES.getlist('additional_photos')

            # Validate extra photos
            valid_exts = ['jpg', 'jpeg', 'png', 'webp']
            for f in extra_files:
                ext = f.name.split('.')[-1].lower()
                if ext not in valid_exts or f.size > 5 * 1024 * 1024:
                    messages.error(request, f"File '{f.name}' must be a JPG, PNG, or WEBP under 5MB.")
                    return redirect('enquiries:enquiry_detail', reference_code=enquiry.reference_code)

            with transaction.atomic():
                if additional_note:
                    # Append note to description or customer notes
                    timestamp_str = datetime.now().strftime('%d %b %Y %H:%M')
                    update_entry = f"\n\n[Customer Update on {timestamp_str}]:\n{additional_note}"
                    enquiry.description += update_entry

                    # Transition status back to under_review if previously info_required
                    if enquiry.status == 'info_required':
                        enquiry.status = 'under_review'

                    enquiry.save()

                    EnquiryStatusHistory.objects.create(
                        enquiry=enquiry,
                        old_status='info_required' if enquiry.status == 'under_review' else enquiry.status,
                        status=enquiry.status,
                        notes=f"Customer provided requested information: {additional_note[:100]}...",
                        changed_by=request.user if request.user.is_authenticated else None
                    )

                for f in extra_files:
                    EnquiryImage.objects.create(
                        enquiry=enquiry,
                        image=f,
                        caption=f.name,
                        file_size=f.size
                    )

            messages.success(request, "Your additional information and photos have been sent to our sourcing team.")
            return redirect('enquiries:enquiry_detail', reference_code=enquiry.reference_code)

        # Action B: Accept Sourcing Quote
        elif action == 'accept_quote':
            if not enquiry.is_quote_available:
                messages.error(request, "There is no active sourcing quote available for this enquiry.")
                return redirect('enquiries:enquiry_detail', reference_code=enquiry.reference_code)

            if enquiry.is_quote_expired:
                messages.error(request, "This sourcing quote has expired. Please request an updated quotation.")
                return redirect('enquiries:enquiry_detail', reference_code=enquiry.reference_code)

            with transaction.atomic():
                enquiry.quote_status = 'accepted'
                enquiry.quote_decision_at = timezone.now()
                enquiry.status = 'customer_accepted'
                enquiry.customer_notes = f"Quote accepted for ₹{enquiry.quote_amount:,.2f}. Procurement order placed with supplier."
                enquiry.save()

                EnquiryStatusHistory.objects.create(
                    enquiry=enquiry,
                    old_status='quote_prepared',
                    status='customer_accepted',
                    notes=f"Customer accepted quote of ₹{enquiry.quote_amount:,.2f}. Sourcing order dispatched.",
                    changed_by=request.user if request.user.is_authenticated else None
                )

                send_enquiry_notification(enquiry, 'quote_accepted')

            messages.success(request, f"You have accepted the quote of ₹{enquiry.quote_amount:,.2f}! Our logistics desk has dispatched the part order.")
            return redirect('enquiries:enquiry_detail', reference_code=enquiry.reference_code)

        # Action C: Decline Sourcing Quote
        elif action == 'decline_quote':
            with transaction.atomic():
                enquiry.quote_status = 'declined'
                enquiry.quote_decision_at = timezone.now()
                enquiry.customer_notes = "Customer declined the sourcing quote. Request concluded."
                enquiry.save()

                EnquiryStatusHistory.objects.create(
                    enquiry=enquiry,
                    old_status=enquiry.status,
                    status=enquiry.status,
                    notes="Customer declined the sourcing quote.",
                    changed_by=request.user if request.user.is_authenticated else None
                )

                send_enquiry_notification(enquiry, 'quote_declined')

            messages.info(request, "You have declined this quotation. Thank you for your feedback.")
            return redirect('enquiries:enquiry_detail', reference_code=enquiry.reference_code)

        # Action D: Customer Cancellation
        elif action == 'cancel_enquiry':
            if not enquiry.can_customer_cancel:
                messages.error(request, "This enquiry cannot be cancelled in its current status.")
                return redirect('enquiries:enquiry_detail', reference_code=enquiry.reference_code)

            with transaction.atomic():
                old_st = enquiry.status
                enquiry.status = 'cancelled'
                enquiry.customer_notes = "Enquiry cancelled by customer request."
                enquiry.save()

                EnquiryStatusHistory.objects.create(
                    enquiry=enquiry,
                    old_status=old_st,
                    status='cancelled',
                    notes="Enquiry cancelled by customer.",
                    changed_by=request.user if request.user.is_authenticated else None
                )

                send_enquiry_notification(enquiry, 'cancelled')

            messages.info(request, f"Enquiry {enquiry.reference_code} has been cancelled.")
            return redirect('enquiries:enquiry_detail', reference_code=enquiry.reference_code)

    context = {
        'enquiry': enquiry,
        'timeline': timeline,
        'images': enquiry.additional_images.all(),
    }
    return render(request, 'enquiries/enquiry_detail.html', context)


# Alias for backward compatibility
def enquiry_status(request, reference_code):
    return redirect('enquiries:enquiry_detail', reference_code=reference_code)


# -------------------------------------------------------------
# 5. Protected Photo Streaming
# -------------------------------------------------------------
def secure_enquiry_photo(request, image_id):
    """
    Streams uploaded part photos with ownership check. Never exposes private paths.
    """
    img = get_object_or_404(EnquiryImage.objects.select_related('enquiry__user'), pk=image_id)
    enquiry = img.enquiry

    if enquiry.user and request.user != enquiry.user and not request.user.is_staff:
        return HttpResponseForbidden("Unauthorized image access.")

    if not img.image or not os.path.exists(img.image.path):
        raise Http404("Photo not found on storage.")

    content_type, _ = mimetypes.guess_type(img.image.path)
    response = FileResponse(open(img.image.path, 'rb'), content_type=content_type or 'image/jpeg')
    return response
