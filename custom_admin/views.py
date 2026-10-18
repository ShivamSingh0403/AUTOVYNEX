from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, Count
from django.contrib.auth.models import User
from orders.models import Order, OrderItem
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
    recent_orders = Order.objects.filter(user=user)[:3]
    garage_vehicles = CustomerVehicle.objects.filter(user=user)[:4]
    service_bookings = ServiceBooking.objects.filter(user=user)[:3]
    missing_enquiries = MissingPartEnquiry.objects.filter(user=user)[:3]
    assistance_requests = RoadsideAssistanceRequest.objects.filter(user=user)[:2]
    
    # Financial metrics
    total_spent = Order.objects.filter(user=user).aggregate(s=Sum('total_amount'))['s'] or 0
    total_vehicles = CustomerVehicle.objects.filter(user=user).count()

    context = {
        'recent_orders': recent_orders,
        'garage_vehicles': garage_vehicles,
        'service_bookings': service_bookings,
        'missing_enquiries': missing_enquiries,
        'assistance_requests': assistance_requests,
        'total_spent': total_spent,
        'total_vehicles': total_vehicles,
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
    enquiries = MissingPartEnquiry.objects.all().order_by('-created_at')
    return render(request, 'custom_admin/enquiries.html', {'enquiries': enquiries})


@user_passes_test(is_staff_check, login_url='/accounts/login/')
def admin_enquiry_update(request, enquiry_id):
    enquiry = get_object_or_404(MissingPartEnquiry, pk=enquiry_id)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        quote = request.POST.get('quote_amount')
        admin_notes = request.POST.get('admin_notes', '').strip()

        if new_status:
            enquiry.status = new_status
        if quote:
            enquiry.quote_amount = quote
        enquiry.admin_notes = admin_notes
        enquiry.save()

        messages.success(request, f"Enquiry {enquiry.reference_code} updated successfully!")
        return redirect('custom_admin:admin_enquiries')

    return render(request, 'custom_admin/enquiry_update.html', {'enquiry': enquiry})


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
