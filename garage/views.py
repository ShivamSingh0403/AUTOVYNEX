import os
import mimetypes
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.urls import reverse

from .models import CustomerVehicle, MaintenanceRecord, MaintenanceReminder, VehicleDocument
from .suggestions import generate_maintenance_suggestions
from vehicles.models import VehicleVariant, VehicleMake, VehicleModel
from inventory.models import Product, ProductFitment
from services.models import ServiceBooking


def parse_decimal(val, default='0.00'):
    """Safely convert user input to Decimal, avoiding float arithmetic."""
    try:
        if not val or str(val).strip() == '':
            return Decimal(default)
        # Remove commas if formatted like 1,500.00
        clean_str = str(val).replace(',', '').strip()
        d = Decimal(clean_str)
        return d if d >= Decimal('0.00') else Decimal('0.00')
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)


# -------------------------------------------------------------
# 1. Digital Garage Dashboard
# -------------------------------------------------------------
@login_required
def garage_index(request):
    """
    Digital Garage primary view:
    Shows all vehicles belonging to the authenticated customer,
    fleet health, pending reminders, and quick vehicle management.
    """
    vehicles = CustomerVehicle.objects.filter(
        user=request.user
    ).select_related('variant__model__make').prefetch_related('maintenance_records', 'reminders')

    total_vehicles = vehicles.count()
    all_records = MaintenanceRecord.objects.filter(customer_vehicle__user=request.user)
    total_maintenance_spent = all_records.aggregate(total=Sum('cost'))['total'] or Decimal('0.00')
    
    # Outstanding reminders across fleet
    pending_reminders = MaintenanceReminder.objects.filter(
        customer_vehicle__user=request.user,
        is_completed=False
    ).select_related('customer_vehicle').order_by('due_date')[:6]

    makes = VehicleMake.objects.all().order_by('name')

    context = {
        'vehicles': vehicles,
        'total_vehicles': total_vehicles,
        'total_spent': total_maintenance_spent,
        'pending_reminders': pending_reminders,
        'makes': makes,
    }
    return render(request, 'garage/index.html', context)


# -------------------------------------------------------------
# 2. Add, Edit, Delete and Manage Vehicles
# -------------------------------------------------------------
@login_required
def add_vehicle(request):
    """
    Add a new vehicle to the customer's garage.
    Validates variant existence and production year compatibility.
    """
    if request.method == 'POST':
        variant_id = request.POST.get('variant_id')
        nickname = request.POST.get('nickname', '').strip()
        reg_number = request.POST.get('registration_number', '').strip().upper()
        vin_number = request.POST.get('vin_number', '').strip().upper()
        color = request.POST.get('color', 'Silver').strip()
        is_default = request.POST.get('is_default') == '1' or CustomerVehicle.objects.filter(user=request.user).count() == 0

        # Purchase year validation
        try:
            purchase_year = int(request.POST.get('purchase_year', date.today().year))
        except (ValueError, TypeError):
            purchase_year = date.today().year

        # Mileage validation
        try:
            current_mileage = int(request.POST.get('current_mileage', 0))
            if current_mileage < 0:
                current_mileage = 0
        except (ValueError, TypeError):
            current_mileage = 0

        if not variant_id:
            messages.error(request, "Please choose a vehicle make, model, and trim variant.")
            return redirect('garage:index')

        variant = get_object_or_404(VehicleVariant, pk=variant_id)

        # Validate purchase year falls within model lifespan
        model_start = variant.model.start_year
        model_end = variant.model.end_year or (date.today().year + 1)
        if purchase_year < model_start or purchase_year > model_end:
            messages.error(
                request,
                f"Year {purchase_year} is invalid for {variant.model.make.name} {variant.model.name}. "
                f"Documented production years: {model_start} – {variant.model.end_year or 'Present'}."
            )
            return redirect('garage:index')

        with transaction.atomic():
            if is_default:
                CustomerVehicle.objects.filter(user=request.user).update(is_default=False)

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
def edit_vehicle(request, vehicle_id):
    """
    Edit vehicle details (nickname, registration, VIN, mileage, color, primary status).
    Strict ownership verification.
    """
    vehicle = get_object_or_404(
        CustomerVehicle.objects.select_related('variant__model__make'),
        pk=vehicle_id,
        user=request.user
    )

    if request.method == 'POST':
        nickname = request.POST.get('nickname', '').strip()
        reg_number = request.POST.get('registration_number', '').strip().upper()
        vin_number = request.POST.get('vin_number', '').strip().upper()
        color = request.POST.get('color', vehicle.color).strip()
        is_default = request.POST.get('is_default') == '1'

        try:
            purchase_year = int(request.POST.get('purchase_year', vehicle.purchase_year))
        except (ValueError, TypeError):
            purchase_year = vehicle.purchase_year

        try:
            current_mileage = int(request.POST.get('current_mileage', vehicle.current_mileage))
            if current_mileage < 0:
                current_mileage = vehicle.current_mileage
        except (ValueError, TypeError):
            current_mileage = vehicle.current_mileage

        # Validate year bounds
        model_start = vehicle.variant.model.start_year
        model_end = vehicle.variant.model.end_year or (date.today().year + 1)
        if purchase_year < model_start or purchase_year > model_end:
            messages.error(
                request,
                f"Year {purchase_year} is outside production span ({model_start}–{vehicle.variant.model.end_year or 'Present'})."
            )
            return render(request, 'garage/edit_vehicle.html', {'vehicle': vehicle})

        with transaction.atomic():
            if is_default and not vehicle.is_default:
                CustomerVehicle.objects.filter(user=request.user).update(is_default=False)

            vehicle.nickname = nickname
            vehicle.registration_number = reg_number
            vehicle.vin_number = vin_number
            vehicle.purchase_year = purchase_year
            vehicle.current_mileage = current_mileage
            vehicle.color = color
            vehicle.is_default = is_default
            vehicle.save()

        messages.success(request, f"Updated {vehicle.display_title} successfully.")
        return redirect('garage:vehicle_detail', vehicle_id=vehicle.id)

    return render(request, 'garage/edit_vehicle.html', {'vehicle': vehicle})


@login_required
def delete_vehicle(request, vehicle_id):
    """
    Safely delete a customer vehicle with ownership verification.
    """
    vehicle = get_object_or_404(CustomerVehicle, pk=vehicle_id, user=request.user)

    if request.method == 'POST':
        title = vehicle.display_title
        was_default = vehicle.is_default
        vehicle.delete()

        # If deleted vehicle was primary, promote next available
        if was_default:
            next_vehicle = CustomerVehicle.objects.filter(user=request.user).first()
            if next_vehicle:
                next_vehicle.is_default = True
                next_vehicle.save()

        messages.success(request, f"Vehicle '{title}' has been removed from your garage.")
        return redirect('garage:index')

    return redirect('garage:vehicle_detail', vehicle_id=vehicle.id)


@login_required
def update_odometer(request, vehicle_id):
    """
    Dedicated quick-action endpoint to update current vehicle odometer.
    """
    vehicle = get_object_or_404(CustomerVehicle, pk=vehicle_id, user=request.user)

    if request.method == 'POST':
        try:
            new_mileage = int(request.POST.get('odometer', vehicle.current_mileage))
            if new_mileage < 0:
                messages.error(request, "Odometer reading cannot be negative.")
                return redirect('garage:vehicle_detail', vehicle_id=vehicle.id)
            if new_mileage < vehicle.current_mileage:
                messages.warning(request, f"New reading ({new_mileage:,} km) is lower than previous reading ({vehicle.current_mileage:,} km). Updated as requested.")
            else:
                messages.success(request, f"Odometer reading updated to {new_mileage:,} km.")
            vehicle.current_mileage = new_mileage
            vehicle.save()
        except (ValueError, TypeError):
            messages.error(request, "Invalid odometer reading provided.")

    return redirect('garage:vehicle_detail', vehicle_id=vehicle.id)


@login_required
def set_default_vehicle(request, vehicle_id):
    """
    Sets the specified vehicle as the primary vehicle for the user.
    """
    vehicle = get_object_or_404(CustomerVehicle, pk=vehicle_id, user=request.user)
    with transaction.atomic():
        CustomerVehicle.objects.filter(user=request.user).update(is_default=False)
        vehicle.is_default = True
        vehicle.save()

    request.session['selected_variant_id'] = vehicle.variant.id
    messages.success(request, f"{vehicle.display_title} is now your primary garage vehicle!")
    return redirect('garage:index')


# -------------------------------------------------------------
# 3. Vehicle Health Overview & Detail
# -------------------------------------------------------------
@login_required
def vehicle_detail(request, vehicle_id):
    """
    Comprehensive Vehicle Detail view:
    - Vehicle specifications
    - Odometer status & quick update
    - Rule-based maintenance health estimations (with explicit disclaimer)
    - Smart maintenance suggestions engine
    - Maintenance history records with cost breakdown
    - Active and completed reminders
    - Document vault with secure download links
    - Compatible spare parts in stock
    - Service bookings history
    """
    vehicle = get_object_or_404(
        CustomerVehicle.objects.select_related('variant__model__make'),
        pk=vehicle_id,
        user=request.user
    )

    maintenance_records = MaintenanceRecord.objects.filter(customer_vehicle=vehicle).order_by('-service_date', '-id')
    reminders = MaintenanceReminder.objects.filter(customer_vehicle=vehicle).order_by('is_completed', 'due_date')
    documents = VehicleDocument.objects.filter(customer_vehicle=vehicle).order_by('-uploaded_at')

    # Aggregated expenses for this vehicle
    vehicle_spent = maintenance_records.aggregate(total=Sum('cost'))['total'] or Decimal('0.00')

    # Smart Maintenance Suggestions
    suggestions = generate_maintenance_suggestions(vehicle)

    # Compatible spare parts in inventory for this variant
    compatible_parts = Product.objects.filter(
        fitments__variant=vehicle.variant,
        is_active=True
    ).select_related('category', 'brand')[:8]

    # Service bookings associated with this car
    search_queries = Q(vehicle_info__icontains=vehicle.variant.model.name)
    if vehicle.registration_number:
        search_queries |= Q(vehicle_info__icontains=vehicle.registration_number)
    service_bookings = ServiceBooking.objects.filter(
        user=request.user
    ).filter(search_queries).order_by('-created_at')[:5]

    # Active reminders for the "link to reminder" dropdown in Add Record modal
    active_reminders = reminders.filter(is_completed=False)

    context = {
        'vehicle': vehicle,
        'maintenance_records': maintenance_records,
        'reminders': reminders,
        'active_reminders': active_reminders,
        'documents': documents,
        'vehicle_spent': vehicle_spent,
        'suggestions': suggestions,
        'compatible_parts': compatible_parts,
        'service_bookings': service_bookings,
        'service_types': MaintenanceRecord.SERVICE_TYPES,
        'doc_types': VehicleDocument.DOC_TYPES,
        'reminder_types': MaintenanceReminder.REMINDER_TYPES,
    }
    return render(request, 'garage/vehicle_detail.html', context)


# -------------------------------------------------------------
# 4. Service and Maintenance History
# -------------------------------------------------------------
@login_required
def add_maintenance_record(request, vehicle_id):
    """
    Log a new maintenance activity with granular cost breakdown (labour, parts, other)
    calculated on server with Decimal arithmetic.
    Optionally completes a selected related reminder.
    """
    vehicle = get_object_or_404(CustomerVehicle, pk=vehicle_id, user=request.user)

    if request.method == 'POST':
        service_title = request.POST.get('service_title', '').strip()
        service_type = request.POST.get('service_type', 'general_service')
        service_date = request.POST.get('service_date')
        workshop = request.POST.get('workshop_name', '').strip()
        notes = request.POST.get('notes', '').strip()

        # Mileage
        try:
            mileage = int(request.POST.get('mileage', vehicle.current_mileage))
        except (ValueError, TypeError):
            mileage = vehicle.current_mileage

        # Granular Cost breakdown with Decimal
        labour_cost = parse_decimal(request.POST.get('labour_cost'))
        parts_cost = parse_decimal(request.POST.get('parts_cost'))
        other_cost = parse_decimal(request.POST.get('other_cost'))

        # If user submitted a single lump sum 'cost' field and granular are 0
        lump_sum = parse_decimal(request.POST.get('cost'))
        if (labour_cost + parts_cost + other_cost) == Decimal('0.00') and lump_sum > Decimal('0.00'):
            labour_cost = lump_sum

        next_service_date = request.POST.get('next_service_date') or None
        next_service_odometer_raw = request.POST.get('next_service_odometer')
        next_service_odometer = int(next_service_odometer_raw) if next_service_odometer_raw and next_service_odometer_raw.isdigit() else None

        # Related reminder to complete
        related_reminder_id = request.POST.get('related_reminder_id')

        # Invoice validation
        invoice = request.FILES.get('invoice_file')
        if invoice:
            if invoice.size > 5 * 1024 * 1024:
                messages.error(request, "Invoice file exceeds the 5MB size limit.")
                return redirect('garage:vehicle_detail', vehicle_id=vehicle.id)
            ext = invoice.name.split('.')[-1].lower()
            if ext not in ['pdf', 'jpg', 'jpeg', 'png', 'webp']:
                messages.error(request, "Invalid invoice format. Allowed formats: PDF, JPG, PNG, WEBP.")
                return redirect('garage:vehicle_detail', vehicle_id=vehicle.id)

        if not (service_date and workshop):
            messages.error(request, "Please enter service date and workshop/provider name.")
            return redirect('garage:vehicle_detail', vehicle_id=vehicle.id)

        with transaction.atomic():
            record = MaintenanceRecord(
                customer_vehicle=vehicle,
                service_title=service_title or dict(MaintenanceRecord.SERVICE_TYPES).get(service_type, 'Service'),
                service_type=service_type,
                service_date=service_date,
                mileage=mileage,
                workshop_name=workshop,
                labour_cost=labour_cost,
                parts_cost=parts_cost,
                other_cost=other_cost,
                notes=notes,
                next_service_date=next_service_date,
                next_service_odometer=next_service_odometer,
                invoice_file=invoice
            )
            record.save()

            # Update car mileage if higher
            if mileage > vehicle.current_mileage:
                vehicle.current_mileage = mileage
                vehicle.save()

            # Complete selected related reminder if provided
            if related_reminder_id:
                try:
                    rel_rem = MaintenanceReminder.objects.get(
                        pk=related_reminder_id,
                        customer_vehicle=vehicle,
                        is_completed=False
                    )
                    rel_rem.is_completed = True
                    rel_rem.completed_at = timezone.now()
                    rel_rem.save()

                    # If recurring, spawn next iteration
                    if rel_rem.recurrence_months or rel_rem.recurrence_km:
                        _spawn_recurring_reminder(rel_rem, vehicle)

                    messages.info(request, f"Related reminder '{rel_rem.title}' marked completed!")
                except MaintenanceReminder.DoesNotExist:
                    pass

        messages.success(request, f"Service '{record.service_title}' logged! Total: ₹{record.cost:,.2f}")
        return redirect('garage:vehicle_detail', vehicle_id=vehicle.id)

    # GET request: render standalone form if accessed directly
    context = {
        'vehicle': vehicle,
        'service_types': MaintenanceRecord.SERVICE_TYPES,
        'active_reminders': vehicle.reminders.filter(is_completed=False),
        'default_title': request.GET.get('service_title', '')
    }
    return render(request, 'garage/add_record.html', context)


@login_required
def edit_maintenance_record(request, record_id):
    """
    Edit an existing maintenance log entry.
    Verifies ownership of the vehicle.
    """
    record = get_object_or_404(
        MaintenanceRecord.objects.select_related('customer_vehicle'),
        pk=record_id,
        customer_vehicle__user=request.user
    )
    vehicle = record.customer_vehicle

    if request.method == 'POST':
        record.service_title = request.POST.get('service_title', record.service_title).strip()
        record.service_type = request.POST.get('service_type', record.service_type)
        record.service_date = request.POST.get('service_date', record.service_date)
        record.workshop_name = request.POST.get('workshop_name', record.workshop_name).strip()
        record.notes = request.POST.get('notes', '').strip()

        try:
            record.mileage = int(request.POST.get('mileage', record.mileage))
        except (ValueError, TypeError):
            pass

        record.labour_cost = parse_decimal(request.POST.get('labour_cost'), default=str(record.labour_cost))
        record.parts_cost = parse_decimal(request.POST.get('parts_cost'), default=str(record.parts_cost))
        record.other_cost = parse_decimal(request.POST.get('other_cost'), default=str(record.other_cost))

        record.next_service_date = request.POST.get('next_service_date') or None
        next_odo = request.POST.get('next_service_odometer')
        record.next_service_odometer = int(next_odo) if next_odo and next_odo.isdigit() else None

        new_invoice = request.FILES.get('invoice_file')
        if new_invoice:
            if new_invoice.size > 5 * 1024 * 1024:
                messages.error(request, "Invoice exceeds 5MB size limit.")
                return render(request, 'garage/edit_record.html', {'record': record, 'vehicle': vehicle, 'service_types': MaintenanceRecord.SERVICE_TYPES})
            ext = new_invoice.name.split('.')[-1].lower()
            if ext not in ['pdf', 'jpg', 'jpeg', 'png', 'webp']:
                messages.error(request, "Invalid file format for invoice.")
                return render(request, 'garage/edit_record.html', {'record': record, 'vehicle': vehicle, 'service_types': MaintenanceRecord.SERVICE_TYPES})
            record.invoice_file = new_invoice

        record.save()
        messages.success(request, f"Maintenance record '{record.service_title}' updated.")
        return redirect('garage:vehicle_detail', vehicle_id=vehicle.id)

    return render(request, 'garage/edit_record.html', {
        'record': record,
        'vehicle': vehicle,
        'service_types': MaintenanceRecord.SERVICE_TYPES
    })


@login_required
def delete_maintenance_record(request, record_id):
    """
    Delete a maintenance record after verifying vehicle ownership.
    """
    record = get_object_or_404(MaintenanceRecord, pk=record_id, customer_vehicle__user=request.user)
    vehicle_id = record.customer_vehicle.id
    title = record.service_title
    record.delete()
    messages.success(request, f"Maintenance record '{title}' has been deleted.")
    return redirect('garage:vehicle_detail', vehicle_id=vehicle_id)


# -------------------------------------------------------------
# 5. Maintenance Reminders Management
# -------------------------------------------------------------
def _spawn_recurring_reminder(completed_reminder, vehicle):
    """Helper to schedule the subsequent cycle for recurring reminders."""
    next_due_date = None
    next_due_mileage = None

    if completed_reminder.recurrence_months:
        base_date = completed_reminder.due_date or date.today()
        # Approximate months as 30 days
        next_due_date = base_date + timedelta(days=completed_reminder.recurrence_months * 30)

    if completed_reminder.recurrence_km:
        base_mileage = completed_reminder.due_mileage or vehicle.current_mileage
        next_due_mileage = base_mileage + completed_reminder.recurrence_km

    if next_due_date or next_due_mileage:
        MaintenanceReminder.objects.create(
            customer_vehicle=vehicle,
            title=completed_reminder.title,
            reminder_type=completed_reminder.reminder_type,
            priority=completed_reminder.priority,
            due_date=next_due_date,
            due_mileage=next_due_mileage,
            recurrence_months=completed_reminder.recurrence_months,
            recurrence_km=completed_reminder.recurrence_km,
            notes=completed_reminder.notes,
            is_completed=False
        )


@login_required
def add_reminder(request, vehicle_id):
    """
    Create a new maintenance reminder with support for due date, odometer, priority,
    and recurring intervals (months / KM).
    """
    vehicle = get_object_or_404(CustomerVehicle, pk=vehicle_id, user=request.user)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        reminder_type = request.POST.get('reminder_type', 'general_service')
        priority = request.POST.get('priority', 'medium')
        due_date = request.POST.get('due_date') or None
        due_mileage_raw = request.POST.get('due_mileage')
        due_mileage = int(due_mileage_raw) if due_mileage_raw and due_mileage_raw.isdigit() else None

        rec_months_raw = request.POST.get('recurrence_months')
        recurrence_months = int(rec_months_raw) if rec_months_raw and rec_months_raw.isdigit() and int(rec_months_raw) > 0 else None

        rec_km_raw = request.POST.get('recurrence_km')
        recurrence_km = int(rec_km_raw) if rec_km_raw and rec_km_raw.isdigit() and int(rec_km_raw) > 0 else None

        notes = request.POST.get('notes', '').strip()

        if not title:
            messages.error(request, "Please specify a reminder title.")
            return redirect('garage:vehicle_detail', vehicle_id=vehicle.id)

        if not (due_date or due_mileage):
            messages.error(request, "Please specify at least a due date or a target odometer reading.")
            return redirect('garage:vehicle_detail', vehicle_id=vehicle.id)

        MaintenanceReminder.objects.create(
            customer_vehicle=vehicle,
            title=title,
            reminder_type=reminder_type,
            priority=priority,
            due_date=due_date,
            due_mileage=due_mileage,
            recurrence_months=recurrence_months,
            recurrence_km=recurrence_km,
            notes=notes,
            is_completed=False
        )
        messages.success(request, f"Maintenance reminder '{title}' saved!")

    return redirect('garage:vehicle_detail', vehicle_id=vehicle.id)


@login_required
def edit_reminder(request, reminder_id):
    """
    Edit reminder configuration with ownership verification.
    """
    reminder = get_object_or_404(
        MaintenanceReminder.objects.select_related('customer_vehicle'),
        pk=reminder_id,
        customer_vehicle__user=request.user
    )
    vehicle = reminder.customer_vehicle

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, "Title cannot be blank.")
            return redirect('garage:edit_reminder', reminder_id=reminder.id)

        reminder.title = title
        reminder.reminder_type = request.POST.get('reminder_type', reminder.reminder_type)
        reminder.priority = request.POST.get('priority', reminder.priority)
        reminder.due_date = request.POST.get('due_date') or None

        due_mileage_raw = request.POST.get('due_mileage')
        reminder.due_mileage = int(due_mileage_raw) if due_mileage_raw and due_mileage_raw.isdigit() else None

        rec_months_raw = request.POST.get('recurrence_months')
        reminder.recurrence_months = int(rec_months_raw) if rec_months_raw and rec_months_raw.isdigit() and int(rec_months_raw) > 0 else None

        rec_km_raw = request.POST.get('recurrence_km')
        reminder.recurrence_km = int(rec_km_raw) if rec_km_raw and rec_km_raw.isdigit() and int(rec_km_raw) > 0 else None

        reminder.notes = request.POST.get('notes', '').strip()
        reminder.save()

        messages.success(request, f"Reminder '{reminder.title}' updated.")
        return redirect('garage:vehicle_detail', vehicle_id=vehicle.id)

    return render(request, 'garage/edit_reminder.html', {
        'reminder': reminder,
        'vehicle': vehicle,
        'reminder_types': MaintenanceReminder.REMINDER_TYPES,
        'priority_choices': MaintenanceReminder.PRIORITY_CHOICES,
    })


@login_required
def toggle_reminder(request, reminder_id):
    """
    Toggles completion status. If completed and configured with recurrence,
    schedules the next recurrence cycle automatically.
    """
    reminder = get_object_or_404(
        MaintenanceReminder.objects.select_related('customer_vehicle'),
        pk=reminder_id,
        customer_vehicle__user=request.user
    )
    vehicle = reminder.customer_vehicle

    if reminder.is_completed:
        # Re-open
        reminder.is_completed = False
        reminder.completed_at = None
        reminder.save()
        messages.info(request, f"Reminder '{reminder.title}' reactivated.")
    else:
        # Mark Complete
        reminder.is_completed = True
        reminder.completed_at = timezone.now()
        reminder.save()

        if reminder.recurrence_months or reminder.recurrence_km:
            _spawn_recurring_reminder(reminder, vehicle)
            messages.success(request, f"Reminder '{reminder.title}' completed! Next recurrence cycle scheduled.")
        else:
            messages.success(request, f"Reminder '{reminder.title}' marked as completed.")

    return redirect('garage:vehicle_detail', vehicle_id=vehicle.id)


@login_required
def postpone_reminder(request, reminder_id):
    """
    Postpones a reminder by extending its due date (30 days) and/or odometer (+1,000 km).
    """
    reminder = get_object_or_404(
        MaintenanceReminder.objects.select_related('customer_vehicle'),
        pk=reminder_id,
        customer_vehicle__user=request.user
    )
    vehicle = reminder.customer_vehicle

    if request.method == 'POST':
        extend_days = int(request.POST.get('extend_days', 30))
        extend_km = int(request.POST.get('extend_km', 1000))

        if reminder.due_date:
            base_date = max(reminder.due_date, date.today())
            reminder.due_date = base_date + timedelta(days=extend_days)

        if reminder.due_mileage:
            base_km = max(reminder.due_mileage, vehicle.current_mileage)
            reminder.due_mileage = base_km + extend_km
        elif not reminder.due_date:
            # If no due date, add target odometer
            reminder.due_mileage = vehicle.current_mileage + extend_km

        reminder.save()
        messages.info(request, f"Reminder '{reminder.title}' postponed (+{extend_days} days / +{extend_km:,} km).")

    return redirect('garage:vehicle_detail', vehicle_id=vehicle.id)


@login_required
def delete_reminder(request, reminder_id):
    """
    Delete a reminder with ownership verification.
    """
    reminder = get_object_or_404(MaintenanceReminder, pk=reminder_id, customer_vehicle__user=request.user)
    vehicle_id = reminder.customer_vehicle.id
    title = reminder.title
    reminder.delete()
    messages.success(request, f"Reminder '{title}' deleted.")
    return redirect('garage:vehicle_detail', vehicle_id=vehicle_id)


# -------------------------------------------------------------
# 6. Maintenance Expense Tracking & Analytics
# -------------------------------------------------------------
@login_required
def expense_dashboard(request, vehicle_id=None):
    """
    Expense analytics dashboard:
    - View fleet-wide or scoped to a specific vehicle
    - Total recorded expenditure (Decimal)
    - Expenses this current month and current year
    - Spending by service category (Django ORM aggregate)
    - Monthly spending history (last 6 months) for responsive pure SVG/CSS chart
    - Vehicle-to-vehicle spending comparison
    - Clear empty states
    """
    customer_vehicles = CustomerVehicle.objects.filter(user=request.user).select_related('variant__model__make')
    
    selected_vehicle = None
    if vehicle_id:
        selected_vehicle = get_object_or_404(customer_vehicles, pk=vehicle_id)
        records_query = MaintenanceRecord.objects.filter(customer_vehicle=selected_vehicle)
    else:
        records_query = MaintenanceRecord.objects.filter(customer_vehicle__user=request.user)

    today = date.today()
    current_year = today.year
    current_month = today.month

    # Aggregations
    total_spent = records_query.aggregate(total=Sum('cost'))['total'] or Decimal('0.00')
    
    month_spent = records_query.filter(
        service_date__year=current_year,
        service_date__month=current_month
    ).aggregate(total=Sum('cost'))['total'] or Decimal('0.00')

    year_spent = records_query.filter(
        service_date__year=current_year
    ).aggregate(total=Sum('cost'))['total'] or Decimal('0.00')

    # Spending by Category
    category_raw = records_query.values('service_type').annotate(
        total=Sum('cost'),
        count=Count('id')
    ).order_by('-total')

    category_labels = dict(MaintenanceRecord.SERVICE_TYPES)
    categories_breakdown = []
    for item in category_raw:
        cat_key = item['service_type']
        cat_total = item['total'] or Decimal('0.00')
        pct = int(round((cat_total / total_spent * 100))) if total_spent > 0 else 0
        categories_breakdown.append({
            'key': cat_key,
            'name': category_labels.get(cat_key, cat_key.replace('_', ' ').title()),
            'total': cat_total,
            'count': item['count'],
            'percentage': pct,
        })

    # Monthly Trend (Past 6 calendar months)
    monthly_data = []
    max_month_val = Decimal('1.00')
    for i in range(5, -1, -1):
        # Month calculation
        m_year = current_year
        m_month = current_month - i
        while m_month <= 0:
            m_month += 12
            m_year -= 1

        label = date(m_year, m_month, 1).strftime('%b %Y')
        short_label = date(m_year, m_month, 1).strftime('%b')
        m_total = records_query.filter(
            service_date__year=m_year,
            service_date__month=m_month
        ).aggregate(total=Sum('cost'))['total'] or Decimal('0.00')

        if m_total > max_month_val:
            max_month_val = m_total

        monthly_data.append({
            'label': label,
            'short_label': short_label,
            'year': m_year,
            'month': m_month,
            'total': m_total,
        })

    # Compute bar heights for responsive visualization
    for m in monthly_data:
        m['height_pct'] = max(4, int(round((m['total'] / max_month_val) * 100))) if max_month_val > 0 else 4

    # Vehicle-to-vehicle comparison (if customer has multiple vehicles)
    vehicle_comparison = []
    if customer_vehicles.count() > 1:
        fleet_total = MaintenanceRecord.objects.filter(customer_vehicle__user=request.user).aggregate(t=Sum('cost'))['t'] or Decimal('0.00')
        for v in customer_vehicles:
            v_spent = v.maintenance_records.aggregate(t=Sum('cost'))['t'] or Decimal('0.00')
            pct = int(round((v_spent / fleet_total * 100))) if fleet_total > 0 else 0
            vehicle_comparison.append({
                'vehicle': v,
                'total_spent': v_spent,
                'percentage': pct,
                'record_count': v.maintenance_records.count()
            })
        vehicle_comparison.sort(key=lambda x: x['total_spent'], reverse=True)

    # Recent maintenance transactions
    recent_records = records_query.select_related('customer_vehicle__variant__model__make').order_by('-service_date', '-id')[:10]

    context = {
        'selected_vehicle': selected_vehicle,
        'customer_vehicles': customer_vehicles,
        'total_spent': total_spent,
        'month_spent': month_spent,
        'year_spent': year_spent,
        'categories_breakdown': categories_breakdown,
        'monthly_data': monthly_data,
        'vehicle_comparison': vehicle_comparison,
        'recent_records': recent_records,
    }
    return render(request, 'garage/expense_dashboard.html', context)


# -------------------------------------------------------------
# 7. Secure Vehicle Documents Vault
# -------------------------------------------------------------
@login_required
def upload_document(request, vehicle_id):
    """
    Securely uploads a vehicle document (RC, Insurance, PUC, Warranty, etc.).
    Validates file extension and ensures file does not exceed 5MB.
    """
    vehicle = get_object_or_404(CustomerVehicle, pk=vehicle_id, user=request.user)

    if request.method == 'POST':
        doc_type = request.POST.get('doc_type', 'rc')
        title = request.POST.get('title', '').strip()
        doc_file = request.FILES.get('document_file')
        issue_date = request.POST.get('issue_date') or None
        expiry_date = request.POST.get('expiry_date') or None
        notes = request.POST.get('notes', '').strip()

        if not doc_file:
            messages.error(request, "Please select a file to upload.")
            return redirect('garage:vehicle_detail', vehicle_id=vehicle.id)

        if doc_file.size > 5 * 1024 * 1024:
            messages.error(request, "Document exceeds the 5MB size limit.")
            return redirect('garage:vehicle_detail', vehicle_id=vehicle.id)

        ext = doc_file.name.split('.')[-1].lower()
        if ext not in ['pdf', 'jpg', 'jpeg', 'png', 'webp']:
            messages.error(request, "Invalid document format. Allowed: PDF, JPG, PNG, WEBP.")
            return redirect('garage:vehicle_detail', vehicle_id=vehicle.id)

        if not title:
            # Default title to document type display
            doc_type_dict = dict(VehicleDocument.DOC_TYPES)
            title = f"{vehicle.nickname or vehicle.variant.model.name} {doc_type_dict.get(doc_type, 'Document')}"

        doc = VehicleDocument.objects.create(
            customer_vehicle=vehicle,
            doc_type=doc_type,
            title=title,
            document_file=doc_file,
            issue_date=issue_date,
            expiry_date=expiry_date,
            notes=notes
        )

        messages.success(request, f"Document '{doc.title}' uploaded securely to your vehicle vault!")

    return redirect('garage:vehicle_detail', vehicle_id=vehicle.id)


@login_required
def secure_view_document(request, doc_id):
    """
    Streams a private document to the browser inline ONLY if the authenticated user
    is the vehicle owner. Never exposes static storage paths to unauthorized users.
    """
    doc = get_object_or_404(
        VehicleDocument.objects.select_related('customer_vehicle'),
        pk=doc_id,
        customer_vehicle__user=request.user
    )

    if not doc.document_file or not os.path.exists(doc.document_file.path):
        raise Http404("Document file not found on server storage.")

    content_type, _ = mimetypes.guess_type(doc.document_file.path)
    response = FileResponse(
        open(doc.document_file.path, 'rb'),
        content_type=content_type or 'application/octet-stream'
    )
    filename = os.path.basename(doc.document_file.name)
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@login_required
def secure_download_document(request, doc_id):
    """
    Forces download of a vehicle document ONLY if the user is the vehicle owner.
    """
    doc = get_object_or_404(
        VehicleDocument.objects.select_related('customer_vehicle'),
        pk=doc_id,
        customer_vehicle__user=request.user
    )

    if not doc.document_file or not os.path.exists(doc.document_file.path):
        raise Http404("Document file not found on server storage.")

    content_type, _ = mimetypes.guess_type(doc.document_file.path)
    response = FileResponse(
        open(doc.document_file.path, 'rb'),
        content_type=content_type or 'application/octet-stream'
    )
    filename = os.path.basename(doc.document_file.name)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def delete_document(request, doc_id):
    """
    Delete a document file and record with strict ownership check.
    """
    doc = get_object_or_404(VehicleDocument, pk=doc_id, customer_vehicle__user=request.user)
    vehicle_id = doc.customer_vehicle.id
    title = doc.title

    # Remove physical file if present
    if doc.document_file and os.path.exists(doc.document_file.path):
        try:
            os.remove(doc.document_file.path)
        except OSError:
            pass

    doc.delete()
    messages.success(request, f"Document '{title}' deleted.")
    return redirect('garage:vehicle_detail', vehicle_id=vehicle_id)


@login_required
def view_record_invoice(request, record_id):
    """
    Securely views an uploaded service invoice/receipt with ownership verification.
    """
    record = get_object_or_404(
        MaintenanceRecord.objects.select_related('customer_vehicle'),
        pk=record_id,
        customer_vehicle__user=request.user
    )

    if not record.invoice_file or not os.path.exists(record.invoice_file.path):
        raise Http404("Invoice file not found.")

    content_type, _ = mimetypes.guess_type(record.invoice_file.path)
    response = FileResponse(
        open(record.invoice_file.path, 'rb'),
        content_type=content_type or 'application/octet-stream'
    )
    filename = os.path.basename(record.invoice_file.name)
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response
