from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Service, ServiceProvider, ServiceBooking, InstallationRequest
from garage.models import CustomerVehicle


def service_directory(request):
    providers = ServiceProvider.objects.filter(is_active=True).order_by('-rating')
    services = Service.objects.all()

    city_filter = request.GET.get('city')
    if city_filter:
        providers = providers.filter(city__iexact=city_filter)

    category_filter = request.GET.get('category')
    if category_filter:
        services = services.filter(category=category_filter)

    cities = ServiceProvider.objects.values_list('city', flat=True).distinct()

    context = {
        'providers': providers,
        'services': services,
        'cities': cities,
        'selected_city': city_filter,
    }
    return render(request, 'services/directory.html', context)


@login_required
def book_service(request):
    services = Service.objects.all().order_by('category', 'starting_price')
    providers = ServiceProvider.objects.filter(is_active=True).order_by('name')
    customer_vehicles = CustomerVehicle.objects.filter(user=request.user)

    selected_vehicle_id = request.GET.get('vehicle_id')
    selected_vehicle = None
    if selected_vehicle_id:
        selected_vehicle = customer_vehicles.filter(pk=selected_vehicle_id).first()

    selected_service_id = request.GET.get('service_id')
    selected_service = None
    if selected_service_id:
        selected_service = Service.objects.filter(pk=selected_service_id).first()

    selected_category = request.GET.get('category')
    if selected_category and not selected_service:
        selected_service = Service.objects.filter(category=selected_category).first()

    if request.method == 'POST':
        service_id = request.POST.get('service_id')
        provider_id = request.POST.get('provider_id')
        vehicle_info = request.POST.get('vehicle_info', '').strip()
        booking_date = request.POST.get('booking_date')
        time_slot = request.POST.get('time_slot')
        customer_address = request.POST.get('customer_address', '').strip()
        customer_phone = request.POST.get('customer_phone', '').strip()
        problem_description = request.POST.get('problem_description', '').strip()

        if not (service_id and provider_id and booking_date and time_slot and customer_address and customer_phone):
            messages.error(request, "Please fill in all mandatory service appointment fields.")
            return redirect('services:book')

        service = get_object_or_404(Service, pk=service_id)
        provider = get_object_or_404(ServiceProvider, pk=provider_id)

        # Check for slot conflicts (prevent duplicate booking for same provider and time slot)
        conflict = ServiceBooking.objects.filter(
            provider=provider,
            booking_date=booking_date,
            time_slot=time_slot
        ).exclude(status='cancelled').exists()

        if conflict:
            messages.error(request, f"Sorry, {provider.name} is already fully booked for {time_slot} on {booking_date}. Please choose another time slot.")
            return redirect('services:book')

        booking = ServiceBooking.objects.create(
            user=request.user,
            provider=provider,
            service=service,
            vehicle_info=vehicle_info or f"{request.user.username}'s Car",
            booking_date=booking_date,
            time_slot=time_slot,
            customer_address=customer_address,
            customer_phone=customer_phone,
            problem_description=problem_description,
            estimated_cost=service.starting_price,
            is_simulated=True,
            status='confirmed'
        )

        messages.success(request, f"Appointment confirmed! Booking Reference: {booking.booking_number} (Demonstration Simulation).")
        return redirect('services:booking_success', booking_number=booking.booking_number)

    context = {
        'services': services,
        'providers': providers,
        'customer_vehicles': customer_vehicles,
        'selected_vehicle': selected_vehicle,
        'selected_service': selected_service,
        'time_slots': ServiceBooking.TIME_SLOTS,
    }
    return render(request, 'services/book.html', context)


@login_required
def booking_success(request, booking_number):
    booking = get_object_or_404(ServiceBooking, booking_number=booking_number, user=request.user)
    return render(request, 'services/booking_success.html', {'booking': booking})


@login_required
def cancel_booking(request, booking_number):
    booking = get_object_or_404(ServiceBooking, booking_number=booking_number, user=request.user)
    if booking.status in ['confirmed', 'in_progress']:
        booking.status = 'cancelled'
        booking.save()
        messages.info(request, f"Service booking {booking.booking_number} has been cancelled.")
    return redirect('dashboard:customer_dashboard')
