from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import RoadsideAssistanceRequest
from garage.models import CustomerVehicle


def assistance_request_view(request):
    customer_vehicles = []
    if request.user.is_authenticated:
        customer_vehicles = CustomerVehicle.objects.filter(user=request.user)

    if request.method == 'POST':
        contact_name = request.POST.get('contact_name', '').strip()
        contact_phone = request.POST.get('contact_phone', '').strip()
        request_type = request.POST.get('request_type', 'breakdown')
        urgency = request.POST.get('urgency', 'urgent')
        vehicle_details = request.POST.get('vehicle_details', '').strip()
        location_address = request.POST.get('location_address', '').strip()
        city = request.POST.get('city', 'Bengaluru').strip()
        landmark = request.POST.get('landmark', '').strip()
        description = request.POST.get('description', '').strip()

        if not (contact_name and contact_phone and vehicle_details and location_address):
            messages.error(request, "Please fill in all mandatory emergency assistance details.")
            return redirect('assistance:request_view')

        ticket = RoadsideAssistanceRequest.objects.create(
            user=request.user if request.user.is_authenticated else None,
            contact_name=contact_name,
            contact_phone=contact_phone,
            request_type=request_type,
            urgency=urgency,
            vehicle_details=vehicle_details,
            location_address=location_address,
            city=city,
            landmark=landmark,
            description=description,
            status='received',
            assigned_patrol='AUTOVYNEX Rapid Patrol Fleet #8',
            estimated_arrival_minutes=25
        )

        messages.success(request, f"Assistance ticket logged! Ticket #: {ticket.ticket_number} (Simulation Notice: Non-live demo dispatch).")
        return redirect('assistance:ticket_detail', ticket_number=ticket.ticket_number)

    return render(request, 'assistance/request_form.html', {'customer_vehicles': customer_vehicles})


def ticket_detail(request, ticket_number):
    ticket = get_object_or_404(RoadsideAssistanceRequest, ticket_number=ticket_number)
    return render(request, 'assistance/ticket_detail.html', {'ticket': ticket})
