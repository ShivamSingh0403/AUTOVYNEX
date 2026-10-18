from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from .models import CustomerVehicle, MaintenanceRecord, MaintenanceReminder, VehicleDocument
from vehicles.models import VehicleVariant, VehicleMake
from inventory.models import Product, ProductFitment
from services.models import ServiceBooking


@login_required
def garage_index(request):
    vehicles = CustomerVehicle.objects.filter(user=request.user).select_related('variant__model__make')
    
    # Aggregated fleet statistics
    total_vehicles = vehicles.count()
    all_records = MaintenanceRecord.objects.filter(customer_vehicle__user=request.user)
    total_maintenance_spent = all_records.aggregate(total=Sum('cost'))['total'] or 0
    pending_reminders = MaintenanceReminder.objects.filter(customer_vehicle__user=request.user, is_completed=False).order_by('due_date')[:5]

    makes = VehicleMake.objects.all().order_by('name')

    context = {
        'vehicles': vehicles,
        'total_vehicles': total_vehicles,
        'total_spent': total_maintenance_spent,
        'pending_reminders': pending_reminders,
        'makes': makes,
    }
    return render(request, 'garage/index.html', context)


@login_required
def add_vehicle(request):
    if request.method == 'POST':
        variant_id = request.POST.get('variant_id')
        nickname = request.POST.get('nickname', '').strip()
        reg_number = request.POST.get('registration_number', '').strip().upper()
        vin_number = request.POST.get('vin_number', '').strip().upper()
        purchase_year = int(request.POST.get('purchase_year', 2022))
        current_mileage = int(request.POST.get('current_mileage', 25000))
        color = request.POST.get('color', 'Silver').strip()
        is_default = request.POST.get('is_default') == '1' or CustomerVehicle.objects.filter(user=request.user).count() == 0

        if not (variant_id and reg_number):
            messages.error(request, "Please choose a vehicle model variant and provide registration number.")
            return redirect('garage:index')

        variant = get_object_or_404(VehicleVariant, pk=variant_id)

        cv = CustomerVehicle.objects.create(
            user=request.user,
            variant=variant,
            nickname=nickname,
            registration_number=reg_number,
            vin_number=vin_number,
            purchase_year=purchase_year,
            current_mileage=current_mileage,
            color=color,
            is_default=is_default
        )

        messages.success(request, f"Added {cv.display_title} to your Digital Garage!")
        return redirect('garage:vehicle_detail', vehicle_id=cv.id)

    return redirect('garage:index')


@login_required
def vehicle_detail(request, vehicle_id):
    vehicle = get_object_or_404(CustomerVehicle.objects.select_related('variant__model__make'), pk=vehicle_id, user=request.user)

    maintenance_records = MaintenanceRecord.objects.filter(customer_vehicle=vehicle).order_by('-service_date')
    reminders = MaintenanceReminder.objects.filter(customer_vehicle=vehicle).order_by('is_completed', 'due_date')
    documents = VehicleDocument.objects.filter(customer_vehicle=vehicle).order_by('-uploaded_at')

    # Total expenses for this car
    vehicle_spent = maintenance_records.aggregate(total=Sum('cost'))['total'] or 0

    # Compatible spare parts in inventory for this variant
    compatible_parts = Product.objects.filter(
        fitments__variant=vehicle.variant,
        is_active=True
    ).select_related('category', 'brand')[:8]

    # Service bookings associated with this car
    service_bookings = ServiceBooking.objects.filter(
        user=request.user,
        vehicle_info__icontains=vehicle.registration_number
    )[:5]

    context = {
        'vehicle': vehicle,
        'maintenance_records': maintenance_records,
        'reminders': reminders,
        'documents': documents,
        'vehicle_spent': vehicle_spent,
        'compatible_parts': compatible_parts,
        'service_bookings': service_bookings,
    }
    return render(request, 'garage/vehicle_detail.html', context)


@login_required
def set_default_vehicle(request, vehicle_id):
    vehicle = get_object_or_404(CustomerVehicle, pk=vehicle_id, user=request.user)
    vehicle.is_default = True
    vehicle.save()
    request.session['selected_variant_id'] = vehicle.variant.id
    messages.success(request, f"{vehicle.display_title} is now your primary garage vehicle!")
    return redirect('garage:index')


@login_required
def add_maintenance_record(request, vehicle_id):
    vehicle = get_object_or_404(CustomerVehicle, pk=vehicle_id, user=request.user)

    if request.method == 'POST':
        service_date = request.POST.get('service_date')
        mileage = int(request.POST.get('mileage', vehicle.current_mileage))
        service_type = request.POST.get('service_type', 'Scheduled Service')
        cost = request.POST.get('cost', 0)
        workshop = request.POST.get('workshop_name', '').strip()
        notes = request.POST.get('notes', '').strip()
        invoice = request.FILES.get('invoice_file')

        if invoice:
            if invoice.size > 5 * 1024 * 1024:
                messages.error(request, "Invoice file exceeds the 5MB size limit.")
                return redirect('garage:vehicle_detail', vehicle_id=vehicle.id)
            ext = invoice.name.split('.')[-1].lower()
            if ext not in ['pdf', 'jpg', 'jpeg', 'png', 'webp']:
                messages.error(request, "Invalid invoice format. Allowed formats: PDF, JPG, PNG, WEBP.")
                return redirect('garage:vehicle_detail', vehicle_id=vehicle.id)

        if service_date and cost and workshop:
            MaintenanceRecord.objects.create(
                customer_vehicle=vehicle,
                service_date=service_date,
                mileage=mileage,
                service_type=service_type,
                cost=cost,
                workshop_name=workshop,
                notes=notes,
                invoice_file=invoice
            )
            # Update car mileage if higher
            if mileage > vehicle.current_mileage:
                vehicle.current_mileage = mileage
                vehicle.save()

            messages.success(request, "Service entry recorded in maintenance log!")
        else:
            messages.error(request, "Please enter service date, workshop name, and expense amount.")

    return redirect('garage:vehicle_detail', vehicle_id=vehicle.id)


@login_required
def add_reminder(request, vehicle_id):
    vehicle = get_object_or_404(CustomerVehicle, pk=vehicle_id, user=request.user)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        reminder_type = request.POST.get('reminder_type', 'general_service')
        due_date = request.POST.get('due_date') or None
        due_mileage = request.POST.get('due_mileage') or None
        notes = request.POST.get('notes', '').strip()

        if title:
            MaintenanceReminder.objects.create(
                customer_vehicle=vehicle,
                title=title,
                reminder_type=reminder_type,
                due_date=due_date,
                due_mileage=due_mileage if due_mileage else None,
                notes=notes
            )
            messages.success(request, f"Reminder '{title}' created!")
        else:
            messages.error(request, "Please specify a reminder title.")

    return redirect('garage:vehicle_detail', vehicle_id=vehicle.id)


@login_required
def toggle_reminder(request, reminder_id):
    reminder = get_object_or_404(MaintenanceReminder, pk=reminder_id, customer_vehicle__user=request.user)
    reminder.is_completed = not reminder.is_completed
    reminder.save()
    status_str = "completed" if reminder.is_completed else "marked active"
    messages.info(request, f"Reminder '{reminder.title}' {status_str}.")
    return redirect('garage:vehicle_detail', vehicle_id=reminder.customer_vehicle.id)


@login_required
def upload_document(request, vehicle_id):
    vehicle = get_object_or_404(CustomerVehicle, pk=vehicle_id, user=request.user)

    if request.method == 'POST':
        doc_type = request.POST.get('doc_type', 'rc')
        title = request.POST.get('title', '').strip()
        doc_file = request.FILES.get('document_file')
        expiry_date = request.POST.get('expiry_date') or None
        notes = request.POST.get('notes', '').strip()

        if doc_file:
            if doc_file.size > 5 * 1024 * 1024:
                messages.error(request, "Document exceeds the 5MB size limit.")
                return redirect('garage:vehicle_detail', vehicle_id=vehicle.id)
            ext = doc_file.name.split('.')[-1].lower()
            if ext not in ['pdf', 'jpg', 'jpeg', 'png', 'webp']:
                messages.error(request, "Invalid document format. Allowed formats: PDF, JPG, PNG, WEBP.")
                return redirect('garage:vehicle_detail', vehicle_id=vehicle.id)

        if title and doc_file:
            VehicleDocument.objects.create(
                customer_vehicle=vehicle,
                doc_type=doc_type,
                title=title,
                document_file=doc_file,
                expiry_date=expiry_date,
                notes=notes
            )
            messages.success(request, f"Document '{title}' uploaded securely!")
        else:
            messages.error(request, "Please provide document title and select a file to upload.")

    return redirect('garage:vehicle_detail', vehicle_id=vehicle.id)
