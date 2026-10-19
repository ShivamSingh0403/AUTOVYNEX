from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, Count
from django.contrib.auth.models import User
from orders.models import Order, OrderItem, CartItem
from inventory.models import Product, ProductCategory, Brand, InventoryRecord
from garage.models import CustomerVehicle, MaintenanceRecord, MaintenanceReminder
from services.models import ServiceBooking, ServiceProvider, Service
from enquiries.models import MissingPartEnquiry
from used_cars.models import UsedCarListing
from assistance.models import RoadsideAssistanceRequest


def is_staff_check(user):
    return user.is_authenticated and user.is_staff


# --- Page 26: Customer Dashboard ---
@login_required
def customer_dashboard(request):
    user = request.user
    recent_orders = Order.objects.filter(user=user).prefetch_related('items').order_by('-created_at')[:4]
    garage_vehicles = CustomerVehicle.objects.filter(user=user).select_related('variant__model__make')
    primary_vehicle = garage_vehicles.filter(is_default=True).first() or garage_vehicles.first()
    
    upcoming_reminders = MaintenanceReminder.objects.filter(
        customer_vehicle__user=user,
        is_completed=False
    ).select_related('customer_vehicle').order_by('due_date')[:5]

    recent_services = MaintenanceRecord.objects.filter(
        customer_vehicle__user=user
    ).select_related('customer_vehicle').order_by('-service_date', '-id')[:5]

    total_maintenance_spent = MaintenanceRecord.objects.filter(
        customer_vehicle__user=user
    ).aggregate(s=Sum('cost'))['s'] or 0

    service_bookings = ServiceBooking.objects.filter(user=user).order_by('-created_at')[:4]
    missing_enquiries = MissingPartEnquiry.objects.filter(user=user)[:3]
    assistance_requests = RoadsideAssistanceRequest.objects.filter(user=user)[:2]
    
    # Financial & Shopping metrics
    total_spent = Order.objects.filter(user=user).aggregate(s=Sum('total_amount'))['s'] or 0
    total_vehicles = garage_vehicles.count()
    cart_count = CartItem.objects.filter(user=user).count()
    profile = getattr(user, 'profile', None)
    saved_vehicle = getattr(profile, 'selected_vehicle', None)

    context = {
        'recent_orders': recent_orders,
        'garage_vehicles': garage_vehicles[:4],
        'primary_vehicle': primary_vehicle,
        'upcoming_reminders': upcoming_reminders,
        'recent_services': recent_services,
        'total_maintenance_spent': total_maintenance_spent,
        'service_bookings': service_bookings,
        'missing_enquiries': missing_enquiries,
        'assistance_requests': assistance_requests,
        'total_spent': total_spent,
        'total_vehicles': total_vehicles,
        'cart_count': cart_count,
        'saved_vehicle': saved_vehicle,
        'profile': profile,
    }
    return render(request, 'dashboard/customer_dashboard.html', context)


# --- Page 15: Custom Admin Dashboard & Control Center ---
@user_passes_test(is_staff_check, login_url='/accounts/login/')
def dashboard_overview(request):
    total_orders = Order.objects.count()
    total_revenue = Order.objects.aggregate(rev=Sum('total_amount'))['rev'] or 0
    total_products = Product.objects.count()
    total_users = User.objects.count()
    total_bookings = ServiceBooking.objects.count()
    pending_enquiries = MissingPartEnquiry.objects.filter(status__in=['submitted', 'under_review', 'searching']).count()
    active_assistance = RoadsideAssistanceRequest.objects.filter(status__in=['received', 'assigned', 'dispatched']).count()
    pending_cars = UsedCarListing.objects.filter(is_approved=False).count()

    recent_orders = Order.objects.all()[:5]
    recent_enquiries = MissingPartEnquiry.objects.all()[:4]
    recent_bookings = ServiceBooking.objects.all()[:4]
    recent_assistance = RoadsideAssistanceRequest.objects.all()[:4]

    # Category breakdown for charts
    categories = ProductCategory.objects.annotate(prod_count=Count('products')).order_by('-prod_count')[:6]

    context = {
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_products': total_products,
        'total_users': total_users,
        'total_bookings': total_bookings,
        'pending_enquiries': pending_enquiries,
        'active_assistance': active_assistance,
        'pending_cars': pending_cars,
        'recent_orders': recent_orders,
        'recent_enquiries': recent_enquiries,
        'recent_bookings': recent_bookings,
        'recent_assistance': recent_assistance,
        'categories': categories,
    }
    return render(request, 'custom_admin/overview.html', context)


@user_passes_test(is_staff_check, login_url='/accounts/login/')
def admin_orders(request):
    orders = Order.objects.all().order_by('-created_at')
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)

    return render(request, 'custom_admin/orders.html', {'orders': orders, 'selected_status': status_filter})


@user_passes_test(is_staff_check, login_url='/accounts/login/')
def admin_order_update(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        tracking_no = request.POST.get('tracking_number', '').strip()
        if new_status:
            order.status = new_status
        if tracking_no:
            order.tracking_number = tracking_no
        order.save()
        messages.success(request, f"Order {order.order_number} status updated to {order.get_status_display()}!")
        return redirect('custom_admin:admin_orders')

    return render(request, 'custom_admin/order_update.html', {'order': order})


@user_passes_test(is_staff_check, login_url='/accounts/login/')
def admin_inventory(request):
    products = Product.objects.all().select_related('category', 'brand').order_by('stock_quantity')[:50]
    
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        new_qty = int(request.POST.get('new_stock', 0))
        prod = get_object_or_404(Product, pk=product_id)
        prev = prod.stock_quantity
        prod.stock_quantity = new_qty
        prod.save()

        InventoryRecord.objects.create(
            product=prod,
            change_type='adjustment',
            quantity=new_qty - prev,
            previous_stock=prev,
            new_stock=new_qty,
            notes='Manual admin audit adjustment'
        )
        messages.success(request, f"Updated stock for {prod.name} to {new_qty} units.")
        return redirect('custom_admin:admin_inventory')

    return render(request, 'custom_admin/inventory.html', {'products': products})


@user_passes_test(is_staff_check, login_url='/accounts/login/')
def admin_enquiries(request):
    enquiries_qs = MissingPartEnquiry.objects.all().prefetch_related('additional_images', 'status_history').order_by('-created_at')

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        enquiries_qs = enquiries_qs.filter(
            Q(reference_code__icontains=q) |
            Q(part_name__icontains=q) |
            Q(contact_name__icontains=q) |
            Q(contact_phone__icontains=q) |
            Q(contact_email__icontains=q) |
            Q(make__icontains=q) |
            Q(model_name__icontains=q) |
            Q(part_number__icontains=q)
        )

    # Status Filter
    status_filter = request.GET.get('status')
    if status_filter:
        enquiries_qs = enquiries_qs.filter(status=status_filter)

    # Category Filter
    category_filter = request.GET.get('category')
    if category_filter:
        enquiries_qs = enquiries_qs.filter(category=category_filter)

    categories = MissingPartEnquiry.CATEGORY_CHOICES
    statuses = MissingPartEnquiry.STATUS_CHOICES

    context = {
        'enquiries': enquiries_qs,
        'search_query': q,
        'selected_status': status_filter,
        'selected_category': category_filter,
        'statuses': statuses,
        'categories': categories,
    }
    return render(request, 'custom_admin/enquiries.html', context)


@user_passes_test(is_staff_check, login_url='/accounts/login/')
def admin_enquiry_update(request, enquiry_id):
    enquiry = get_object_or_404(
        MissingPartEnquiry.objects.prefetch_related('additional_images', 'status_history'),
        pk=enquiry_id
    )

    if request.method == 'POST':
        action = request.POST.get('action', 'update_status')

        # Action 1: Status & Notes Update
        if action == 'update_status':
            new_status = request.POST.get('status')
            customer_note = request.POST.get('customer_notes', '').strip()
            internal_note = request.POST.get('internal_notes', '').strip()

            if not enquiry.can_transition_to(new_status, request.user):
                messages.error(request, f"Invalid status transition from {enquiry.get_status_display()} to {dict(MissingPartEnquiry.STATUS_CHOICES).get(new_status, new_status)}.")
                return redirect('custom_admin:admin_enquiry_update', enquiry_id=enquiry.id)

            old_st = enquiry.status
            enquiry.status = new_status
            if customer_note:
                enquiry.customer_notes = customer_note
            if internal_note:
                enquiry.internal_notes = internal_note
            enquiry.save()

            from enquiries.models import EnquiryStatusHistory
            from enquiries.notifications import send_enquiry_notification

            EnquiryStatusHistory.objects.create(
                enquiry=enquiry,
                old_status=old_st,
                status=new_status,
                notes=customer_note or f"Status changed to {enquiry.get_status_display()}.",
                internal_notes=internal_note,
                changed_by=request.user
            )

            # Customer Notification
            event_type = 'info_required' if new_status == 'info_required' else ('completed' if new_status == 'completed' else 'sourcing_update')
            send_enquiry_notification(enquiry, event_type)

            messages.success(request, f"Enquiry {enquiry.reference_code} updated to '{enquiry.get_status_display()}'.")
            return redirect('custom_admin:admin_enquiry_update', enquiry_id=enquiry.id)

        # Action 2: Prepare Sourcing Quote
        elif action == 'prepare_quote':
            quote_raw = request.POST.get('quote_amount', '').strip()
            quote_brand = request.POST.get('quote_brand', '').strip()
            quote_part_num = request.POST.get('quote_part_number', '').strip()
            quote_condition = request.POST.get('quote_condition', 'Brand New OEM Genuine').strip()
            quote_delivery = request.POST.get('quote_delivery_days', '3–5 Business Days').strip()
            quote_warranty = request.POST.get('quote_warranty', '6 Months AUTOVYNEX Warranty').strip()
            quote_notes = request.POST.get('quote_notes', '').strip()

            try:
                from decimal import Decimal
                clean_str = quote_raw.replace(',', '').strip()
                quote_val = Decimal(clean_str)
            except Exception:
                quote_val = Decimal('0.00')

            if quote_val <= Decimal('0.00'):
                messages.error(request, "Please enter a valid positive quote price in INR.")
                return redirect('custom_admin:admin_enquiry_update', enquiry_id=enquiry.id)

            old_st = enquiry.status
            enquiry.quote_amount = quote_val
            enquiry.quote_brand = quote_brand
            enquiry.quote_part_number = quote_part_num
            enquiry.quote_condition = quote_condition
            enquiry.quote_delivery_days = quote_delivery
            enquiry.quote_warranty = quote_warranty
            enquiry.quote_notes = quote_notes
            enquiry.quote_status = 'pending'
            from django.utils import timezone
            from datetime import timedelta
            enquiry.quote_expires_at = timezone.now() + timedelta(days=7)
            enquiry.status = 'quote_prepared'
            enquiry.customer_notes = f"Verified quote prepared for ₹{quote_val:,.2f} ({quote_brand or 'OEM'}). Delivery: {quote_delivery}."
            enquiry.save()

            from enquiries.models import EnquiryStatusHistory
            from enquiries.notifications import send_enquiry_notification

            EnquiryStatusHistory.objects.create(
                enquiry=enquiry,
                old_status=old_st,
                status='quote_prepared',
                notes=f"Official quote of ₹{quote_val:,.2f} prepared by sourcing agent.",
                changed_by=request.user
            )

            send_enquiry_notification(enquiry, 'quote_prepared')

            messages.success(request, f"Official quote of ₹{quote_val:,.2f} prepared and notified to customer!")
            return redirect('custom_admin:admin_enquiry_update', enquiry_id=enquiry.id)

    statuses = MissingPartEnquiry.STATUS_CHOICES
    history = enquiry.status_history.all().order_by('-created_at')

    context = {
        'enquiry': enquiry,
        'statuses': statuses,
        'history': history,
        'images': enquiry.additional_images.all(),
    }
    return render(request, 'custom_admin/enquiry_update.html', context)


@user_passes_test(is_staff_check, login_url='/accounts/login/')
def admin_services(request):
    bookings = ServiceBooking.objects.all().order_by('-booking_date')
    if request.method == 'POST':
        booking_id = request.POST.get('booking_id')
        new_status = request.POST.get('status')
        bk = get_object_or_404(ServiceBooking, pk=booking_id)
        bk.status = new_status
        bk.save()
        messages.success(request, f"Booking {bk.booking_number} updated to {bk.get_status_display()}!")
        return redirect('custom_admin:admin_services')

    return render(request, 'custom_admin/services.html', {'bookings': bookings})


@user_passes_test(is_staff_check, login_url='/accounts/login/')
def admin_assistance(request):
    requests_list = RoadsideAssistanceRequest.objects.all().order_by('-created_at')
    if request.method == 'POST':
        req_id = request.POST.get('request_id')
        new_status = request.POST.get('status')
        patrol = request.POST.get('assigned_patrol', '').strip()
        ticket = get_object_or_404(RoadsideAssistanceRequest, pk=req_id)
        if new_status:
            ticket.status = new_status
        if patrol:
            ticket.assigned_patrol = patrol
        ticket.save()
        messages.success(request, f"Assistance Ticket {ticket.ticket_number} updated!")
        return redirect('custom_admin:admin_assistance')

    return render(request, 'custom_admin/assistance.html', {'requests_list': requests_list})
