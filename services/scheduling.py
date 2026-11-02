import datetime
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from accounts.models import Notification
from .models import (
    ServiceProvider, ProviderSchedule, ProviderUnavailableDate,
    ServiceBooking, ServiceBookingHistory, ServiceCompletionRecord
)


def format_time_12h(t: datetime.time) -> str:
    """Format a datetime.time object to 12-hour AM/PM string, e.g. 09:00 AM."""
    return t.strftime("%I:%M %p")


def parse_time_slot_string(slot_str: str):
    """
    Parses a time slot string like '09:00 - 10:00 AM' or '09:00 AM - 10:00 AM'
    Returns (start_time, end_time) as datetime.time objects.
    """
    try:
        clean = slot_str.replace("AM", " AM").replace("PM", " PM").strip()
        parts = [p.strip() for p in clean.split("-") if p.strip()]
        if len(parts) >= 2:
            # Check if first part has AM/PM or borrows from second
            p1, p2 = parts[0], parts[1]
            if "AM" not in p1 and "PM" not in p1:
                # borrow AM/PM from p2 if present
                if "PM" in p2:
                    p1_str = f"{p1} PM" if int(p1.split(':')[0]) == 12 or int(p1.split(':')[0]) < 8 else f"{p1} AM"
                else:
                    p1_str = f"{p1} AM"
            else:
                p1_str = p1
            
            p2_str = p2
            
            t1 = datetime.datetime.strptime(p1_str.strip(), "%I:%M %p").time()
            t2 = datetime.datetime.strptime(p2_str.strip(), "%I:%M %p").time()
            return t1, t2
    except Exception:
        pass
    # Fallback to 09:00 - 10:00
    return datetime.time(9, 0), datetime.time(10, 0)


def get_available_slots(provider: ServiceProvider, target_date: datetime.date, service=None):
    """
    Computes real availability time slots for a given provider on target_date.
    Returns:
        dict: {
            'is_open': bool,
            'reason': str (if closed),
            'slots': list of dicts with slot info
        }
    """
    today = datetime.date.today()
    if target_date < today:
        return {
            'is_open': False,
            'reason': "Past dates are not eligible for booking.",
            'slots': []
        }

    # Check unavailable dates / holidays
    unavailable = ProviderUnavailableDate.objects.filter(provider=provider, date=target_date).first()
    if unavailable:
        return {
            'is_open': False,
            'reason': f"Workshop is closed on this date: {unavailable.reason}",
            'slots': []
        }

    # Check weekly operating schedule
    weekday = target_date.weekday()
    schedule = ProviderSchedule.objects.filter(provider=provider, weekday=weekday).first()
    if schedule and schedule.is_closed:
        day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][weekday]
        return {
            'is_open': False,
            'reason': f"The workshop is regularly closed on {day_name}s.",
            'slots': []
        }

    slot_minutes = schedule.slot_duration_minutes if schedule else 60
    max_capacity = schedule.max_bookings_per_slot if schedule else 1
    open_time = schedule.open_time if schedule else datetime.time(9, 0)
    close_time = schedule.close_time if schedule else datetime.time(18, 0)
    has_break = schedule.has_break if schedule else True
    break_start = schedule.break_start if schedule else datetime.time(13, 0)
    break_end = schedule.break_end if schedule else datetime.time(14, 0)

    # Query active bookings on this date for the provider
    active_bookings = ServiceBooking.objects.filter(
        provider=provider,
        booking_date=target_date
    ).exclude(status__in=['cancelled', 'rejected'])

    # Map booked counts per slot string / start time
    booked_counts = {}
    for b in active_bookings:
        key = b.time_slot.strip()
        booked_counts[key] = booked_counts.get(key, 0) + 1

    # Generate slots from open_time to close_time
    current_dt = datetime.datetime.combine(target_date, open_time)
    close_dt = datetime.datetime.combine(target_date, close_time)
    now_dt = datetime.datetime.now()

    slots_list = []
    delta = datetime.timedelta(minutes=slot_minutes)

    while current_dt + delta <= close_dt:
        slot_start = current_dt.time()
        slot_end = (current_dt + delta).time()

        # Check if overlaps with lunch / break period
        is_in_break = False
        if has_break and break_start and break_end:
            # Overlaps if slot_start < break_end and slot_end > break_start
            if slot_start < break_end and slot_end > break_start:
                is_in_break = True

        if not is_in_break:
            slot_label = f"{format_time_12h(slot_start)} - {format_time_12h(slot_end)}"
            
            # Check if this slot is already past today
            is_past = False
            if target_date == today and current_dt <= now_dt:
                is_past = True

            booked_num = booked_counts.get(slot_label, 0)
            spots_left = max(0, max_capacity - booked_num)
            is_available = (spots_left > 0) and not is_past

            status_text = "Available"
            if is_past:
                status_text = "Past"
            elif spots_left == 0:
                status_text = "Full"

            slots_list.append({
                'slot_label': slot_label,
                'start_time': slot_start.strftime("%H:%M:%S"),
                'end_time': slot_end.strftime("%H:%M:%S"),
                'formatted_start': format_time_12h(slot_start),
                'formatted_end': format_time_12h(slot_end),
                'capacity': max_capacity,
                'booked': booked_num,
                'spots_left': spots_left,
                'is_available': is_available,
                'status_text': status_text,
            })

        current_dt += delta

    return {
        'is_open': True,
        'reason': "",
        'schedule_summary': f"{format_time_12h(open_time)} - {format_time_12h(close_time)}",
        'slots': slots_list
    }


def validate_and_reserve_slot(provider, target_date, slot_label):
    """
    Validates availability with atomic database locking to prevent race conditions / double bookings.
    Must be called within or creates transaction.atomic().
    Returns (True, start_time, end_time) on success, or (False, error_message, None) on failure.
    """
    availability = get_available_slots(provider, target_date)
    if not availability['is_open']:
        return False, availability['reason'], None

    # Locking check on existing bookings
    weekday = target_date.weekday()
    schedule = ProviderSchedule.objects.filter(provider=provider, weekday=weekday).first()
    max_capacity = schedule.max_bookings_per_slot if schedule else 1

    with transaction.atomic():
        if schedule:
            ProviderSchedule.objects.select_for_update().filter(pk=schedule.pk).exists()

        current_booked = ServiceBooking.objects.select_for_update().filter(
            provider=provider,
            booking_date=target_date,
            time_slot__iexact=slot_label.strip()
        ).exclude(status__in=['cancelled', 'rejected']).count()

        if current_booked >= max_capacity:
            return False, f"Sorry, {provider.name} is already fully booked for {slot_label} on {target_date}. Please choose another time slot.", None

        t_start, t_end = parse_time_slot_string(slot_label)
        return True, t_start, t_end


VALID_TRANSITIONS = {
    'pending': ['confirmed', 'rejected', 'cancelled'],
    'confirmed': ['in_progress', 'rescheduled', 'cancelled'],
    'rescheduled': ['confirmed', 'in_progress', 'cancelled'],
    'in_progress': ['completed', 'cancelled'],
    'completed': [],
    'rejected': [],
    'cancelled': [],
}


def transition_booking_status(booking: ServiceBooking, new_status: str, actor=None, customer_note='', cancellation_reason=''):
    """
    Safely transitions booking status, creates audit trail, and dispatches in-app notifications.
    """
    if new_status == booking.status:
        return True, "Status remains unchanged."

    allowed = VALID_TRANSITIONS.get(booking.status, [])
    if new_status not in allowed:
        return False, f"Invalid transition from '{booking.get_status_display()}' to '{new_status}'."

    prev_status = booking.status
    booking.status = new_status
    if cancellation_reason:
        booking.cancellation_reason = cancellation_reason
    booking.save()

    # Log history
    ServiceBookingHistory.objects.create(
        booking=booking,
        previous_status=prev_status,
        new_status=new_status,
        changed_by=actor,
        customer_note=customer_note or cancellation_reason or f"Status updated to {new_status}."
    )

    # In-app notification to customer
    status_display = booking.get_status_display()
    notif_msg = f"Your service booking {booking.booking_number} for {booking.service.name} at {booking.provider.name} is now: {status_display}."
    if customer_note:
        notif_msg += f" Note: {customer_note}"

    Notification.objects.create(
        user=booking.user,
        title=f"Booking Update: {status_display}",
        message=notif_msg,
        link=f"/services/my-bookings/{booking.booking_number}/",
        notification_type='service'
    )

    # Simulated Console Email Output
    print(f"\n[SIMULATED EMAIL NOTIFICATION]")
    print(f"To: {booking.user.email or booking.user.username}")
    print(f"Subject: AUTOVYNEX Service Booking {booking.booking_number} - {status_display}")
    print(f"Dear {booking.user.first_name or booking.user.username},")
    print(f"Your appointment status has been updated to '{status_display}'.")
    print(f"Provider: {booking.provider.name} | Date: {booking.booking_date} | Slot: {booking.time_slot}")
    if customer_note:
        print(f"Notes from workshop: {customer_note}")
    print("----------------------------------------------------------------------\n")

    return True, f"Booking status successfully updated to {status_display}."


def complete_service_booking(
    booking: ServiceBooking,
    actor,
    labour_charges: Decimal,
    parts_charges: Decimal,
    other_charges: Decimal,
    odometer_reading: int,
    work_performed: str,
    parts_replaced: str = '',
    technician_notes: str = '',
    next_service_date=None,
    next_service_odometer=None,
    mark_paid: bool = True
):
    """
    Completes a service booking:
    1. Sets booking status to 'completed'.
    2. Calculates final bill amount.
    3. Creates ServiceCompletionRecord.
    4. Automatically creates or updates MaintenanceRecord in customer's Digital Garage if a vehicle is linked.
    5. Creates audit log and notifications.
    """
    total = (labour_charges or Decimal('0.00')) + (parts_charges or Decimal('0.00')) + (other_charges or Decimal('0.00'))
    
    booking.final_amount = total
    if mark_paid:
        booking.payment_status = 'paid_at_workshop'
    booking.status = 'completed'
    booking.save()

    # Link / create MaintenanceRecord in Digital Garage if customer_vehicle is present
    linked_maint_rec = None
    if booking.customer_vehicle:
        from garage.models import MaintenanceRecord, MaintenanceReminder
        veh = booking.customer_vehicle
        
        # Update current mileage if new reading is higher
        if odometer_reading and odometer_reading > veh.current_mileage:
            veh.current_mileage = odometer_reading
            veh.save(update_fields=['current_mileage', 'updated_at'])

        linked_maint_rec = MaintenanceRecord.objects.create(
            customer_vehicle=veh,
            service_title=f"{booking.service.name} ({booking.provider.name})",
            service_date=booking.booking_date,
            mileage=odometer_reading or veh.current_mileage,
            service_type='Scheduled Service',
            labour_cost=labour_charges or Decimal('0.00'),
            parts_cost=parts_charges or Decimal('0.00'),
            other_cost=other_charges or Decimal('0.00'),
            cost=total,
            workshop_name=booking.provider.name,
            notes=f"Work done: {work_performed}. Parts: {parts_replaced}. Tech Notes: {technician_notes}",
            next_service_date=next_service_date,
            next_service_odometer=next_service_odometer
        )

        if next_service_date:
            MaintenanceReminder.objects.create(
                customer_vehicle=veh,
                title=f"Next Periodic Service ({booking.service.name})",
                reminder_type='general_service',
                due_date=next_service_date,
                due_mileage=next_service_odometer,
                priority='medium'
            )

    comp_rec = ServiceCompletionRecord.objects.create(
        booking=booking,
        work_performed=work_performed,
        parts_replaced=parts_replaced,
        labour_charges=labour_charges,
        parts_charges=parts_charges,
        other_charges=other_charges,
        final_amount=total,
        odometer_reading=odometer_reading,
        technician_notes=technician_notes,
        next_service_recommendation_date=next_service_date,
        next_service_recommendation_odometer=next_service_odometer,
        linked_maintenance_record=linked_maint_rec
    )

    # Log history
    ServiceBookingHistory.objects.create(
        booking=booking,
        previous_status='in_progress',
        new_status='completed',
        changed_by=actor,
        customer_note=f"Service successfully completed. Final invoice amount: ₹{total:,.2f}. Recorded in Digital Garage."
    )

    # In-app notification
    Notification.objects.create(
        user=booking.user,
        title="Vehicle Service Completed!",
        message=f"Work on your vehicle for {booking.service.name} at {booking.provider.name} is complete. Total: ₹{total:,.2f}. Service record logged in your Digital Garage.",
        link=f"/services/my-bookings/{booking.booking_number}/",
        notification_type='service'
    )

    return comp_rec
