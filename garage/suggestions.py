"""
Smart Maintenance Suggestion Engine for AUTOVYNEX Digital Garage.

IMPORTANT NOTE:
All suggestions produced by this engine are rule-based advisory estimates
calculated strictly from customer-entered records, odometer readings, and configured
reminder thresholds. AUTOVYNEX does not claim to measure live OBD-II telemetry,
mechanical wear, or sensor data without dedicated telematics hardware, nor does it
use unverified machine-learning claims.
"""
from datetime import date, timedelta
from django.urls import reverse


def generate_maintenance_suggestions(vehicle):
    """
    Analyzes a CustomerVehicle and its associated maintenance records, reminders,
    and documents to produce transparent, rule-based maintenance suggestions.
    
    Each suggestion includes:
    - title: Brief recommendation title
    - badge: 'Urgent', 'Due Soon', 'Recommended', or 'Advisory'
    - badge_class: CSS badge class ('danger', 'warning', 'primary', 'info')
    - reason: Explicit explanation of the exact data and threshold used
    - action_label: Button text
    - action_url: Navigation URL
    - icon: Automotive SVG icon name / category
    """
    suggestions = []
    today = date.today()
    current_km = vehicle.current_mileage or 0

    # 1. Overdue & Due Soon Reminders check
    active_reminders = vehicle.reminders.filter(is_completed=False).order_by('due_date')
    for rem in active_reminders:
        state = rem.status_state
        if state == 'overdue':
            reason_parts = []
            if rem.due_date and rem.due_date < today:
                days_over = (today - rem.due_date).days
                reason_parts.append(f"scheduled date {rem.due_date.strftime('%d %b %Y')} passed {days_over} days ago")
            if rem.due_mileage and current_km >= rem.due_mileage:
                km_over = current_km - rem.due_mileage
                reason_parts.append(f"odometer {current_km:,} km exceeded due threshold {rem.due_mileage:,} km (+{km_over:,} km)")

            reason_str = " & ".join(reason_parts) if reason_parts else "maintenance deadline passed"
            suggestions.append({
                'id': f'reminder-overdue-{rem.id}',
                'title': f"Overdue Reminder: {rem.title}",
                'badge': 'Overdue',
                'badge_class': 'badge-danger',
                'reason': f"Calculated from your custom reminder: {reason_str}.",
                'action_label': 'Log Service Now',
                'action_url': f"{reverse('garage:add_record', args=[vehicle.id])}?service_title={rem.title}",
                'category': 'reminder',
                'priority': 1
            })
        elif state == 'due_soon':
            reason_parts = []
            if rem.due_date:
                days_left = (rem.due_date - today).days
                reason_parts.append(f"due in {days_left} days ({rem.due_date.strftime('%d %b %Y')})")
            if rem.due_mileage:
                km_left = rem.due_mileage - current_km
                reason_parts.append(f"{km_left:,} km remaining before {rem.due_mileage:,} km")

            suggestions.append({
                'id': f'reminder-due-soon-{rem.id}',
                'title': f"Upcoming: {rem.title}",
                'badge': 'Due Soon',
                'badge_class': 'badge-warning',
                'reason': f"Calculated from your custom reminder: {', '.join(reason_parts)}.",
                'action_label': 'View / Complete',
                'action_url': reverse('garage:vehicle_detail', args=[vehicle.id]) + '#reminders',
                'category': 'reminder',
                'priority': 2
            })

    # 2. Engine Oil & Filter Service heuristic
    last_oil_service = vehicle.maintenance_records.filter(
        service_type__in=['oil_change', 'oil_filter', 'general_service']
    ).order_by('-service_date').first()

    oil_km_interval = 10000  # standard recommended interval
    oil_days_interval = 365  # 1 year

    if last_oil_service:
        km_since_oil = current_km - last_oil_service.mileage if current_km >= last_oil_service.mileage else 0
        days_since_oil = (today - last_oil_service.service_date).days

        if km_since_oil >= oil_km_interval or days_since_oil >= oil_days_interval:
            suggestions.append({
                'id': 'oil-change-due',
                'title': 'Engine Oil & Filter Service Due',
                'badge': 'Recommended',
                'badge_class': 'badge-warning',
                'reason': (
                    f"Last recorded on {last_oil_service.service_date.strftime('%d %b %Y')} at "
                    f"{last_oil_service.mileage:,} km ({km_since_oil:,} km and {days_since_oil} days ago). "
                    f"Standard interval is {oil_km_interval:,} km or 12 months."
                ),
                'action_label': 'Book Service',
                'action_url': f"{reverse('services:book')}?vehicle_id={vehicle.id}&service=oil_change",
                'category': 'oil',
                'priority': 2
            })
    elif current_km >= 5000 and not vehicle.maintenance_records.exists():
        suggestions.append({
            'id': 'initial-service-log',
            'title': 'Establish Maintenance Baseline',
            'badge': 'Advisory',
            'badge_class': 'badge-info',
            'reason': (
                f"No service records logged yet for odometer {current_km:,} km. "
                "Adding past service logs helps monitor engine fluid longevity and warranty compliance."
            ),
            'action_label': 'Add Past Service Record',
            'action_url': reverse('garage:add_record', args=[vehicle.id]),
            'category': 'general',
            'priority': 4
        })

    # 3. Document Expiry Alerts (Insurance, Pollution, Registration)
    docs = vehicle.documents.filter(expiry_date__isnull=False)
    for doc in docs:
        if doc.expiry_date:
            days_until_expiry = (doc.expiry_date - today).days
            if days_until_expiry < 0:
                suggestions.append({
                    'id': f'doc-expired-{doc.id}',
                    'title': f"{doc.get_doc_type_display()} Has Expired",
                    'badge': 'Urgent',
                    'badge_class': 'badge-danger',
                    'reason': (
                        f"Stored document '{doc.title}' expired on {doc.expiry_date.strftime('%d %b %Y')} "
                        f"({abs(days_until_expiry)} days ago)."
                    ),
                    'action_label': 'Upload Renewed Document',
                    'action_url': reverse('garage:vehicle_detail', args=[vehicle.id]) + '#documents',
                    'category': 'document',
                    'priority': 1
                })
            elif days_until_expiry <= 30:
                suggestions.append({
                    'id': f'doc-expiring-{doc.id}',
                    'title': f"{doc.get_doc_type_display()} Expiry Approaching",
                    'badge': 'Due Soon',
                    'badge_class': 'badge-warning',
                    'reason': (
                        f"Document '{doc.title}' is valid until {doc.expiry_date.strftime('%d %b %Y')} "
                        f"({days_until_expiry} days remaining)."
                    ),
                    'action_label': 'View Document',
                    'action_url': reverse('garage:vehicle_detail', args=[vehicle.id]) + '#documents',
                    'category': 'document',
                    'priority': 3
                })

    # 4. Next Service Date recorded on latest maintenance record
    latest_record_with_next = vehicle.maintenance_records.filter(
        next_service_date__isnull=False
    ).order_by('-service_date').first()

    if latest_record_with_next and latest_record_with_next.next_service_date:
        next_date = latest_record_with_next.next_service_date
        days_to_next = (next_date - today).days
        if 0 <= days_to_next <= 21:
            suggestions.append({
                'id': f'next-service-scheduled-{latest_record_with_next.id}',
                'title': 'Workshop Scheduled Service Approaching',
                'badge': 'Due Soon',
                'badge_class': 'badge-warning',
                'reason': (
                    f"Workshop '{latest_record_with_next.workshop_name}' specified next service on "
                    f"{next_date.strftime('%d %b %Y')} ({days_to_next} days away)."
                ),
                'action_label': 'Book Appointment',
                'action_url': f"{reverse('services:book')}?vehicle_id={vehicle.id}",
                'category': 'service',
                'priority': 2
            })
        elif days_to_next < 0:
            suggestions.append({
                'id': f'next-service-overdue-{latest_record_with_next.id}',
                'title': 'Scheduled Service Passed',
                'badge': 'Overdue',
                'badge_class': 'badge-danger',
                'reason': (
                    f"Workshop specified next service date was {next_date.strftime('%d %b %Y')} "
                    f"({abs(days_to_next)} days ago)."
                ),
                'action_label': 'Log New Service Record',
                'action_url': reverse('garage:add_record', args=[vehicle.id]),
                'category': 'service',
                'priority': 1
            })

    # 5. Mileage Milestone Advisory (e.g. 40k, 60k, 80k km)
    major_milestones = [20000, 40000, 60000, 80000, 100000, 120000]
    for ms in major_milestones:
        if current_km >= ms and (current_km - ms) <= 2000:
            # Check if there is already a brake/transmission/coolant check around here
            has_major_check = vehicle.maintenance_records.filter(
                service_type__in=['brake_pad', 'coolant', 'tyre', 'general_service'],
                mileage__gte=ms - 2000
            ).exists()
            if not has_major_check:
                suggestions.append({
                    'id': f'milestone-{ms}',
                    'title': f'{ms:,} km Inspection Milestone',
                    'badge': 'Advisory',
                    'badge_class': 'badge-info',
                    'reason': (
                        f"Current odometer is {current_km:,} km. Vehicles crossing {ms:,} km "
                        "typically benefit from brake pad inspection, coolant check, and tyre rotation."
                    ),
                    'action_label': 'Browse Spare Parts',
                    'action_url': f"{reverse('inventory:product_list')}?vehicle={vehicle.id}",
                    'category': 'parts',
                    'priority': 4
                })
            break

    # Sort suggestions by priority (1 = highest urgency)
    suggestions.sort(key=lambda s: s.get('priority', 99))
    return suggestions
