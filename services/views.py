import datetime
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Min, Q
from django.utils.dateparse import parse_date

from .models import (
    ServiceProvider, ServiceCategory, Service, ProviderService,
    ProviderSchedule, ProviderUnavailableDate, ServiceBooking,
    ServiceBookingHistory, ServiceCompletionRecord, ServiceEnquiry
)
from .forms import (
    ServiceBookingForm, ServiceEnquiryForm, ServiceCompletionForm,
    ProviderScheduleForm, ProviderServiceForm, ProviderUnavailableDateForm
)
from .scheduling import (
    get_available_slots, validate_and_reserve_slot,
    transition_booking_status, complete_service_booking
)
from garage.models import CustomerVehicle
from vehicles.models import VehicleMake


def service_directory(request):
    """
    Service Centre Marketplace Directory.
    Server-side filtering by city, postal code, category, brand, price, availability, and search query.
    """
    providers = ServiceProvider.objects.filter(is_active=True).annotate(
        min_configured_price=Min('provider_services__price')
    )

    # Search query
    q = request.GET.get('q', '').strip()
    if q:
        providers = providers.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(city__icontains=q) |
            Q(address__icontains=q) |
            Q(facilities__icontains=q) |
            Q(provider_services__service__name__icontains=q)
        ).distinct()

    # City filter
    city_filter = request.GET.get('city', '').strip()
    if city_filter:
        providers = providers.filter(city__iexact=city_filter)

    # Postal code filter
    postal_code = request.GET.get('postal_code', '').strip()
    if postal_code:
        providers = providers.filter(postal_code__icontains=postal_code)

    # Service Category filter
    category_slug = request.GET.get('category', '').strip()
    if category_slug:
        providers = providers.filter(
            provider_services__service__category_ref__slug=category_slug,
            provider_services__is_available=True
        ).distinct()

    # Vehicle Brand supported filter
    brand_id = request.GET.get('brand', '').strip()
    if brand_id and brand_id.isdigit():
        providers = providers.filter(supported_brands__id=int(brand_id)).distinct()

    # Price range filter
    min_price = request.GET.get('min_price', '').strip()
    if min_price and min_price.isdigit():
        providers = providers.filter(min_configured_price__gte=Decimal(min_price))

    max_price = request.GET.get('max_price', '').strip()
    if max_price and max_price.isdigit():
        providers = providers.filter(min_configured_price__lte=Decimal(max_price))

    # Workshop availability filter
    availability = request.GET.get('availability', '').strip()
    if availability == 'active':
        providers = providers.filter(status='active')

    # Sorting
    sort = request.GET.get('sort', '').strip()
    if sort == 'name':
        providers = providers.order_by('name')
    elif sort == 'price_asc':
        providers = providers.order_by('min_configured_price', 'name')
    elif sort == 'newest':
        providers = providers.order_by('-created_at')
    else:
        # Default sort: verified first, then name
        providers = providers.order_by('-is_verified', 'name')

    # Pagination: 9 per page
    paginator = Paginator(providers, 9)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Filter dropdown context datasets
    cities = ServiceProvider.objects.filter(is_active=True).values_list('city', flat=True).distinct().order_by('city')
    categories = ServiceCategory.objects.filter(is_active=True).order_by('sort_order', 'name')
    brands = VehicleMake.objects.all().order_by('name')

    # Query string for pagination links
    query_params = request.GET.copy()
    if 'page' in query_params:
        query_params.pop('page')
    querystring = query_params.urlencode()

    context = {
        'page_obj': page_obj,
        'providers': page_obj.object_list,
        'cities': cities,
        'categories': categories,
        'brands': brands,
        'selected_city': city_filter,
        'selected_postal_code': postal_code,
        'selected_category': category_slug,
        'selected_brand': brand_id,
        'min_price': min_price,
        'max_price': max_price,
        'selected_availability': availability,
        'selected_sort': sort,
        'search_query': q,
        'querystring': querystring,
        'total_providers': paginator.count,
    }
    return render(request, 'services/directory.html', context)


def provider_detail(request, slug):
    """
    Detailed Service Centre Profile.
    Displays workshop photographs, information, address, operating hours,
    available services with estimated prices, contact/enquiry option, and booking CTA.
    """
    provider = get_object_or_404(
        ServiceProvider.objects.prefetch_related('supported_brands', 'schedules', 'unavailable_dates'),
        slug=slug,
        is_active=True
    )

    offerings = ProviderService.objects.filter(
        provider=provider,
        is_available=True
    ).select_related('service', 'service__category_ref').order_by('service__category_ref__sort_order', 'price')

    schedules = provider.schedules.all().order_by('weekday')
    unavailable_dates = provider.unavailable_dates.filter(date__gte=datetime.date.today()).order_by('date')[:5]

    enquiry_form = ServiceEnquiryForm()
    if request.method == 'POST' and 'submit_enquiry' in request.POST:
        enquiry_form = ServiceEnquiryForm(request.POST)
        if enquiry_form.is_valid():
            enquiry = enquiry_form.save(commit=False)
            enquiry.provider = provider
            if request.user.is_authenticated:
                enquiry.user = request.user
            enquiry.save()
            messages.success(request, f"Thank you! Your enquiry has been received by {provider.name}. The team will contact you shortly.")
            return redirect('services:provider_detail', slug=provider.slug)

    context = {
        'provider': provider,
        'offerings': offerings,
        'schedules': schedules,
        'unavailable_dates': unavailable_dates,
        'enquiry_form': enquiry_form,
    }
    return render(request, 'services/provider_detail.html', context)


def api_get_slots(request):
    """
    AJAX endpoint returning real operating slots and availability for a provider and date.
    """
    provider_id = request.GET.get('provider_id')
    date_str = request.GET.get('date')

    if not provider_id or not date_str:
        return JsonResponse({'success': False, 'reason': 'Provider ID and appointment date are required.'}, status=400)

    provider = get_object_or_404(ServiceProvider, pk=provider_id, is_active=True)
    target_date = parse_date(date_str)
    if not target_date:
        return JsonResponse({'success': False, 'reason': 'Invalid date format.'}, status=400)

    result = get_available_slots(provider, target_date)
    return JsonResponse({
        'success': True,
        'is_open': result['is_open'],
        'reason': result['reason'],
        'schedule_summary': result.get('schedule_summary', ''),
        'slots': result['slots']
    })


@login_required
def book_service(request):
    """
    Multi-step appointment booking workflow:
    1. Select service centre
    2. Select service
    3. Choose saved vehicle from Digital Garage or enter custom details
    4. Select appointment date
    5. View and select real available time slot
    6. Enter problem notes / symptoms
    7. Review estimated price snapshot
    8. Confirm booking
    """
    customer_vehicles = CustomerVehicle.objects.filter(user=request.user).select_related('variant', 'variant__model', 'variant__model__make')
    providers = ServiceProvider.objects.filter(is_active=True, status='active').order_by('name')
    services = Service.objects.filter(is_active=True).select_related('category_ref').order_by('category_ref__sort_order', 'starting_price')

    # Query pre-selection
    selected_provider_id = request.GET.get('provider_id') or request.GET.get('provider')
    selected_service_id = request.GET.get('service_id') or request.GET.get('service')
    selected_vehicle_id = request.GET.get('vehicle_id')

    preselected_provider = None
    if selected_provider_id:
        if str(selected_provider_id).isdigit():
            preselected_provider = providers.filter(pk=int(selected_provider_id)).first()
        else:
            preselected_provider = providers.filter(slug=selected_provider_id).first()

    preselected_service = None
    if selected_service_id:
        if str(selected_service_id).isdigit():
            preselected_service = services.filter(pk=int(selected_service_id)).first()
        else:
            preselected_service = services.filter(slug=selected_service_id).first()

    preselected_vehicle = None
    if selected_vehicle_id and str(selected_vehicle_id).isdigit():
        preselected_vehicle = customer_vehicles.filter(pk=int(selected_vehicle_id)).first()

    if request.method == 'POST':
        form = ServiceBookingForm(request.POST)
        provider_id = request.POST.get('provider') or request.POST.get('provider_id')
        service_id = request.POST.get('service') or request.POST.get('service_id')
        booking_date_str = request.POST.get('booking_date')
        time_slot = request.POST.get('time_slot', '').strip()
        vehicle_source = request.POST.get('vehicle_source', 'garage')
        customer_vehicle_id = request.POST.get('customer_vehicle_id')
        custom_vehicle_text = request.POST.get('custom_vehicle_text') or request.POST.get('vehicle_info', '').strip()
        customer_phone = request.POST.get('customer_phone', '').strip()
        customer_address = request.POST.get('customer_address', '').strip()
        problem_description = request.POST.get('problem_description', '').strip()

        # Validation
        if not (provider_id and service_id and booking_date_str and time_slot):
            messages.error(request, "Please fill in all required appointment fields including date and time slot.")
            return redirect('services:book')

        provider = get_object_or_404(ServiceProvider, pk=provider_id, is_active=True)
        service = get_object_or_404(Service, pk=service_id, is_active=True)

        if isinstance(booking_date_str, datetime.date):
            target_date = booking_date_str
        else:
            target_date = parse_date(str(booking_date_str))

        if not target_date or target_date < datetime.date.today():
            messages.error(request, "Appointment date cannot be in the past.")
            return redirect('services:book')

        # Real slot availability check with DB locking
        is_valid, t_start_or_err, t_end = validate_and_reserve_slot(provider, target_date, time_slot)
        if not is_valid:
            messages.error(request, t_start_or_err)
            return redirect('services:book')

        # Vehicle association
        chosen_vehicle = None
        vehicle_display_info = custom_vehicle_text
        if vehicle_source == 'garage' and customer_vehicle_id:
            chosen_vehicle = customer_vehicles.filter(pk=customer_vehicle_id).first()
            if chosen_vehicle:
                vehicle_display_info = chosen_vehicle.display_title
                if chosen_vehicle.registration_number:
                    vehicle_display_info += f" [{chosen_vehicle.registration_number}]"

        if not vehicle_display_info:
            vehicle_display_info = f"{request.user.first_name or request.user.username}'s Vehicle"

        # Determine price snapshot
        provider_offering = ProviderService.objects.filter(provider=provider, service=service, is_available=True).first()
        if provider_offering:
            price_snapshot = provider_offering.price
        else:
            price_snapshot = service.starting_price

        # Create booking atomically
        booking = ServiceBooking.objects.create(
            user=request.user,
            provider=provider,
            service=service,
            provider_service=provider_offering,
            customer_vehicle=chosen_vehicle,
            vehicle_info=vehicle_display_info,
            booking_date=target_date,
            start_time=t_start_or_err,
            end_time=t_end,
            time_slot=time_slot,
            status='pending',
            payment_status='unpaid',
            customer_address=customer_address,
            customer_phone=customer_phone,
            problem_description=problem_description,
            estimated_cost=price_snapshot,
            price_estimate_snapshot=price_snapshot,
            is_simulated=True
        )

        # Create initial history log
        ServiceBookingHistory.objects.create(
            booking=booking,
            previous_status='',
            new_status='pending',
            changed_by=request.user,
            customer_note="Booking request placed by customer."
        )

        # Log simulated console email
        print(f"\n[SIMULATED EMAIL NOTIFICATION]")
        print(f"To: {request.user.email or request.user.username}")
        print(f"Subject: AUTOVYNEX Booking Received - {booking.booking_number}")
        print(f"Dear {request.user.first_name or request.user.username},")
        print(f"We have received your appointment request for {service.name} at {provider.name}.")
        print(f"Date: {booking.booking_date} | Slot: {booking.time_slot} | Estimated Cost: INR {price_snapshot:,.2f}")
        print("Status: Pending Approval by Workshop.")
        print("----------------------------------------------------------------------\n")

        messages.success(request, f"Appointment successfully scheduled! Reference Code: {booking.booking_number}")
        return redirect('services:booking_success', booking_number=booking.booking_number)

    form = ServiceBookingForm()
    context = {
        'form': form,
        'providers': providers,
        'services': services,
        'customer_vehicles': customer_vehicles,
        'preselected_provider': preselected_provider,
        'preselected_service': preselected_service,
        'preselected_vehicle': preselected_vehicle,
    }
    return render(request, 'services/book.html', context)


@login_required
def booking_success(request, booking_number):
    """
    Appointment Confirmation View.
    """
    booking = get_object_or_404(
        ServiceBooking.objects.select_related('provider', 'service', 'customer_vehicle'),
        booking_number=booking_number,
        user=request.user
    )
    return render(request, 'services/booking_success.html', {'booking': booking})


@login_required
def my_bookings(request):
    """
    Customer Booking Dashboard ("My Services").
    Categorized into Upcoming, In Progress, Completed, and Cancelled/Rejected.
    """
    all_bookings = ServiceBooking.objects.filter(user=request.user).select_related(
        'provider', 'service', 'customer_vehicle'
    ).order_by('-booking_date', '-created_at')

    active_status_filter = request.GET.get('tab', 'upcoming')

    upcoming_bookings = all_bookings.filter(status__in=['pending', 'confirmed', 'rescheduled'])
    in_progress_bookings = all_bookings.filter(status='in_progress')
    completed_bookings = all_bookings.filter(status='completed')
    cancelled_bookings = all_bookings.filter(status__in=['cancelled', 'rejected'])

    context = {
        'upcoming_bookings': upcoming_bookings,
        'in_progress_bookings': in_progress_bookings,
        'completed_bookings': completed_bookings,
        'cancelled_bookings': cancelled_bookings,
        'active_tab': active_status_filter,
        'total_bookings': all_bookings.count(),
    }
    return render(request, 'services/my_bookings.html', context)


@login_required
def booking_detail(request, booking_number):
    """
    Detailed Booking View for Customer and Workshop Owners.
    Includes status workflow progress stepper, timeline history, price breakdown, and cancellation/reschedule actions.
    """
    booking = get_object_or_404(
        ServiceBooking.objects.select_related('provider', 'service', 'customer_vehicle'),
        booking_number=booking_number
    )

    # Permission check: must be the customer, provider owner, or staff
    is_owner = (booking.user == request.user)
    is_provider = (booking.provider.owner == request.user) or request.user.is_staff

    if not (is_owner or is_provider):
        return HttpResponseForbidden("You are not authorized to view this appointment record.")

    history_logs = booking.history_logs.select_related('changed_by').order_by('-created_at')
    completion_details = getattr(booking, 'completion_record', None)

    context = {
        'booking': booking,
        'history_logs': history_logs,
        'completion_details': completion_details,
        'is_customer': is_owner,
        'is_provider': is_provider,
    }
    return render(request, 'services/booking_detail.html', context)


@login_required
def cancel_booking(request, booking_number):
    """
    Customer cancellation action with optional cancellation note.
    """
    booking = get_object_or_404(ServiceBooking, booking_number=booking_number, user=request.user)

    if request.method == 'POST':
        if not booking.can_be_cancelled:
            messages.error(request, f"This booking is currently '{booking.get_status_display()}' and cannot be cancelled.")
            return redirect('services:booking_detail', booking_number=booking.booking_number)

        reason = request.POST.get('cancellation_reason', '').strip() or "Cancelled by customer."
        success, msg = transition_booking_status(
            booking=booking,
            new_status='cancelled',
            actor=request.user,
            customer_note=f"Cancelled by customer: {reason}",
            cancellation_reason=reason
        )

        if success:
            messages.success(request, f"Appointment {booking.booking_number} has been cancelled.")
        else:
            messages.error(request, msg)

    return redirect('services:booking_detail', booking_number=booking.booking_number)


@login_required
def reschedule_booking(request, booking_number):
    """
    Customer reschedule request picking a new date and time slot.
    """
    booking = get_object_or_404(ServiceBooking, booking_number=booking_number, user=request.user)

    if request.method == 'POST':
        if not booking.can_be_rescheduled:
            messages.error(request, f"This booking is currently '{booking.get_status_display()}' and cannot be rescheduled.")
            return redirect('services:booking_detail', booking_number=booking.booking_number)

        new_date_str = request.POST.get('reschedule_date')
        new_slot = request.POST.get('reschedule_slot', '').strip()
        reason = request.POST.get('reschedule_reason', '').strip()

        new_date = parse_date(new_date_str) if new_date_str else None
        if not new_date or new_date < datetime.date.today():
            messages.error(request, "Please choose a valid upcoming appointment date.")
            return redirect('services:booking_detail', booking_number=booking.booking_number)

        is_valid, t_start_or_err, t_end = validate_and_reserve_slot(booking.provider, new_date, new_slot)
        if not is_valid:
            messages.error(request, t_start_or_err)
            return redirect('services:booking_detail', booking_number=booking.booking_number)

        old_date_str = f"{booking.booking_date} ({booking.time_slot})"
        booking.booking_date = new_date
        booking.time_slot = new_slot
        booking.start_time = t_start_or_err
        booking.end_time = t_end
        booking.save()

        transition_booking_status(
            booking=booking,
            new_status='rescheduled',
            actor=request.user,
            customer_note=f"Rescheduled from {old_date_str} to {new_date} ({new_slot}). Reason: {reason or 'Customer schedule adjustment'}"
        )

        messages.success(request, f"Appointment {booking.booking_number} has been successfully rescheduled to {new_date} {new_slot}!")

    return redirect('services:booking_detail', booking_number=booking.booking_number)


# ==============================================================================
# WORKSHOP / SERVICE PROVIDER PORTAL
# ==============================================================================

def get_authorized_provider(user, provider_id=None):
    """Helper verifying that the user owns the provider or is a system administrator."""
    if user.is_staff:
        if provider_id:
            return ServiceProvider.objects.filter(pk=provider_id).first()
        return ServiceProvider.objects.first()
    return ServiceProvider.objects.filter(owner=user).first()


@login_required
def provider_dashboard(request):
    """
    Workshop portal for authorized providers to manage appointments, schedules, and services.
    """
    provider = get_authorized_provider(request.user, request.GET.get('provider_id'))
    if not provider:
        messages.warning(request, "You do not currently have an authorized workshop profile linked to your account.")
        return redirect('services:directory')

    all_providers = ServiceProvider.objects.all() if request.user.is_staff else [provider]

    today = datetime.date.today()
    bookings_qs = ServiceBooking.objects.filter(provider=provider).select_related(
        'user', 'service', 'customer_vehicle'
    ).order_by('-booking_date', '-created_at')

    # Status filter
    status_filter = request.GET.get('status', 'all')
    if status_filter != 'all':
        bookings = bookings_qs.filter(status=status_filter)
    else:
        bookings = bookings_qs

    # Metrics
    total_count = bookings_qs.count()
    pending_count = bookings_qs.filter(status='pending').count()
    today_count = bookings_qs.filter(booking_date=today).exclude(status__in=['cancelled', 'rejected']).count()
    in_progress_count = bookings_qs.filter(status='in_progress').count()
    completed_count = bookings_qs.filter(status='completed').count()

    context = {
        'provider': provider,
        'all_providers': all_providers,
        'bookings': bookings[:50],
        'total_count': total_count,
        'pending_count': pending_count,
        'today_count': today_count,
        'in_progress_count': in_progress_count,
        'completed_count': completed_count,
        'selected_status': status_filter,
    }
    return render(request, 'services/provider_dashboard/dashboard.html', context)


@login_required
def provider_update_status(request, booking_number):
    """
    Workshop status updater (e.g. Confirm, Reject, Mark In Progress, Cancel).
    """
    booking = get_object_or_404(ServiceBooking, booking_number=booking_number)
    provider = get_authorized_provider(request.user, booking.provider.id)
    if not provider or provider.id != booking.provider.id:
        return HttpResponseForbidden("Not authorized to manage this workshop's appointments.")

    if request.method == 'POST':
        new_status = request.POST.get('status')
        staff_note = request.POST.get('staff_note', '').strip()

        if new_status:
            success, msg = transition_booking_status(
                booking=booking,
                new_status=new_status,
                actor=request.user,
                customer_note=staff_note or f"Status changed to {booking.get_status_display()} by service centre."
            )
            if success:
                messages.success(request, msg)
            else:
                messages.error(request, msg)

    return redirect('services:provider_dashboard')


@login_required
def provider_complete_booking(request, booking_number):
    """
    Workshop service completion endpoint.
    Records labour charges, parts charges, odometer, notes, and auto-creates Digital Garage MaintenanceRecord.
    """
    booking = get_object_or_404(ServiceBooking, booking_number=booking_number)
    provider = get_authorized_provider(request.user, booking.provider.id)
    if not provider or provider.id != booking.provider.id:
        return HttpResponseForbidden("Not authorized to manage this workshop's appointments.")

    if request.method == 'POST':
        form = ServiceCompletionForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            comp_rec = complete_service_booking(
                booking=booking,
                actor=request.user,
                labour_charges=cd['labour_charges'],
                parts_charges=cd['parts_charges'],
                other_charges=cd['other_charges'],
                odometer_reading=cd['odometer_reading'],
                work_performed=cd['work_performed'],
                parts_replaced=cd['parts_replaced'],
                technician_notes=cd['technician_notes'],
                next_service_date=cd['next_service_recommendation_date'],
                next_service_odometer=cd['next_service_recommendation_odometer'],
                mark_paid=cd['mark_paid']
            )
            messages.success(
                request,
                f"Booking {booking.booking_number} successfully marked as Completed! Total: ₹{comp_rec.final_amount:,.2f}. Synced to Digital Garage."
            )
            return redirect('services:provider_dashboard')
        else:
            messages.error(request, "Please check the form inputs for errors.")

    return redirect('services:booking_detail', booking_number=booking.booking_number)


@login_required
def provider_schedule_manage(request):
    """
    Manage workshop weekly operating hours, breaks, slot duration, and bay capacities.
    """
    provider = get_authorized_provider(request.user, request.GET.get('provider_id'))
    if not provider:
        return redirect('services:directory')

    schedules = provider.schedules.all().order_by('weekday')

    if request.method == 'POST':
        for day in range(7):
            prefix = f"day_{day}_"
            is_closed = request.POST.get(f"{prefix}is_closed") == 'on'
            open_time_str = request.POST.get(f"{prefix}open_time")
            close_time_str = request.POST.get(f"{prefix}close_time")
            has_break = request.POST.get(f"{prefix}has_break") == 'on'
            break_start_str = request.POST.get(f"{prefix}break_start")
            break_end_str = request.POST.get(f"{prefix}break_end")
            slot_mins = int(request.POST.get(f"{prefix}slot_duration", 60))
            max_cap = int(request.POST.get(f"{prefix}max_capacity", 2))

            schedule, _ = ProviderSchedule.objects.get_or_create(provider=provider, weekday=day)
            schedule.is_closed = is_closed
            if open_time_str:
                schedule.open_time = datetime.datetime.strptime(open_time_str, "%H:%M").time()
            if close_time_str:
                schedule.close_time = datetime.datetime.strptime(close_time_str, "%H:%M").time()
            schedule.has_break = has_break
            if break_start_str:
                schedule.break_start = datetime.datetime.strptime(break_start_str, "%H:%M").time()
            if break_end_str:
                schedule.break_end = datetime.datetime.strptime(break_end_str, "%H:%M").time()
            schedule.slot_duration_minutes = slot_mins
            schedule.max_bookings_per_slot = max_cap
            schedule.save()

        messages.success(request, f"Weekly operating schedule for {provider.name} updated successfully.")
        return redirect('services:provider_schedule_manage')

    context = {
        'provider': provider,
        'schedules': schedules,
    }
    return render(request, 'services/provider_dashboard/schedule_manage.html', context)


@login_required
def provider_services_manage(request):
    """
    Manage workshop offered services, custom pricing, and duration.
    """
    provider = get_authorized_provider(request.user, request.GET.get('provider_id'))
    if not provider:
        return redirect('services:directory')

    offerings = ProviderService.objects.filter(provider=provider).select_related('service', 'service__category_ref').order_by('service__category_ref__sort_order')

    if request.method == 'POST':
        for offering in offerings:
            prefix = f"svc_{offering.id}_"
            price_str = request.POST.get(f"{prefix}price")
            duration_str = request.POST.get(f"{prefix}duration")
            is_avail = request.POST.get(f"{prefix}available") == 'on'
            notes = request.POST.get(f"{prefix}notes", '')

            if price_str:
                offering.price = Decimal(price_str)
            if duration_str and duration_str.isdigit():
                offering.duration_minutes = int(duration_str)
            offering.is_available = is_avail
            offering.notes = notes
            offering.save()

        messages.success(request, f"Service catalogue and pricing updated for {provider.name}.")
        return redirect('services:provider_services_manage')

    context = {
        'provider': provider,
        'offerings': offerings,
    }
    return render(request, 'services/provider_dashboard/services_manage.html', context)


@login_required
def provider_unavailable_dates(request):
    """
    Manage workshop holiday and closure dates.
    """
    provider = get_authorized_provider(request.user, request.GET.get('provider_id'))
    if not provider:
        return redirect('services:directory')

    dates = provider.unavailable_dates.all().order_by('date')

    if request.method == 'POST':
        if 'add_date' in request.POST:
            form = ProviderUnavailableDateForm(request.POST)
            if form.is_valid():
                unav = form.save(commit=False)
                unav.provider = provider
                unav.save()
                messages.success(request, f"Added closure on {unav.date} ({unav.reason}).")
                return redirect('services:provider_unavailable_dates')
        elif 'delete_date' in request.POST:
            date_id = request.POST.get('date_id')
            ProviderUnavailableDate.objects.filter(provider=provider, id=date_id).delete()
            messages.info(request, "Holiday closure removed.")
            return redirect('services:provider_unavailable_dates')

    form = ProviderUnavailableDateForm()
    context = {
        'provider': provider,
        'dates': dates,
        'form': form,
    }
    return render(request, 'services/provider_dashboard/unavailable_dates.html', context)
