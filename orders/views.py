from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_POST
from decimal import Decimal
import re
from .models import CartItem, Order, OrderItem
from inventory.models import Product, InventoryRecord
from services.models import InstallationRequest, ServiceProvider
from garage.models import CustomerVehicle


def _get_cart_queryset(request):
    if request.user.is_authenticated:
        return CartItem.objects.filter(user=request.user).select_related('product', 'product__category')
    else:
        if not request.session.session_key:
            request.session.create()
        return CartItem.objects.filter(session_key=request.session.session_key).select_related('product', 'product__category')


def _calculate_cart_totals(cart_items):
    subtotal = sum(item.item_subtotal for item in cart_items)
    # Explicit rules: Free delivery on orders >= ₹1499, otherwise ₹149 flat delivery fee
    if subtotal == 0:
        shipping_fee = Decimal('0.00')
    elif subtotal >= Decimal('1499.00'):
        shipping_fee = Decimal('0.00')
    else:
        shipping_fee = Decimal('149.00')

    # Explicit discount rule: ₹200 savings on orders >= ₹3000
    if subtotal >= Decimal('3000.00'):
        discount = Decimal('200.00')
    else:
        discount = Decimal('0.00')

    installation_total = sum(
        item.product.installation_fee * item.quantity for item in cart_items if item.buy_and_install and item.product.is_installable
    )

    taxable = max(Decimal('0.00'), subtotal - discount)
    tax = taxable * Decimal('0.18')
    total = taxable + shipping_fee + tax

    return {
        'subtotal': subtotal,
        'discount': discount,
        'shipping_fee': shipping_fee,
        'installation_total': installation_total,
        'tax': tax,
        'total': total,
    }


def cart_detail(request):
    cart_items = _get_cart_queryset(request)
    totals = _calculate_cart_totals(cart_items)

    context = {
        'cart_items': cart_items,
        'subtotal': totals['subtotal'],
        'discount': totals['discount'],
        'shipping_fee': totals['shipping_fee'],
        'tax': totals['tax'],
        'total': totals['total'],
        'installation_total': totals['installation_total'],
    }
    return render(request, 'orders/cart.html', context)


@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = 1

    if quantity < 1:
        quantity = 1

    buy_and_install = request.POST.get('buy_and_install') == '1' and product.is_installable

    if not product.in_stock:
        messages.error(request, f"Sorry, {product.name} is currently out of stock.")
        return redirect(request.META.get('HTTP_REFERER', 'inventory:shop'))

    if quantity > product.stock_quantity:
        quantity = product.stock_quantity

    if request.user.is_authenticated:
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user, product=product,
            defaults={'quantity': quantity, 'buy_and_install': buy_and_install}
        )
    else:
        if not request.session.session_key:
            request.session.create()
        cart_item, created = CartItem.objects.get_or_create(
            session_key=request.session.session_key, product=product,
            defaults={'quantity': quantity, 'buy_and_install': buy_and_install}
        )

    if not created:
        cart_item.quantity += quantity
        if cart_item.quantity > product.stock_quantity:
            cart_item.quantity = product.stock_quantity
        if buy_and_install:
            cart_item.buy_and_install = True
        cart_item.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('accept') == 'application/json':
        cart_items = _get_cart_queryset(request)
        new_cart_count = sum(item.quantity for item in cart_items)
        from django.http import JsonResponse
        return JsonResponse({
            'status': 'success',
            'message': f"Added {quantity}x {product.name} to your shopping cart!",
            'cart_count': new_cart_count,
            'product_name': product.name,
            'product_price': str(product.final_price)
        })

    messages.success(request, f"Added {quantity}x {product.name} to your shopping cart!")
    return redirect('orders:cart_detail')


@require_POST
def buy_now(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    if not product.in_stock:
        messages.error(request, f"Sorry, {product.name} is currently out of stock.")
        return redirect('inventory:product_detail', slug=product.slug)

    try:
        quantity = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = 1

    if quantity < 1:
        quantity = 1
    if quantity > product.stock_quantity:
        quantity = product.stock_quantity

    buy_and_install = request.POST.get('buy_and_install') == '1' and product.is_installable

    if request.user.is_authenticated:
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user, product=product,
            defaults={'quantity': quantity, 'buy_and_install': buy_and_install}
        )
    else:
        if not request.session.session_key:
            request.session.create()
        cart_item, created = CartItem.objects.get_or_create(
            session_key=request.session.session_key, product=product,
            defaults={'quantity': quantity, 'buy_and_install': buy_and_install}
        )

    if not created:
        cart_item.quantity = max(cart_item.quantity, quantity)
        if buy_and_install:
            cart_item.buy_and_install = True
        cart_item.save()

    messages.info(request, f"Proceeding to checkout with {product.name}.")
    return redirect('orders:checkout')


@require_POST
def update_cart_item(request, item_id):
    if request.user.is_authenticated:
        cart_item = get_object_or_404(CartItem, pk=item_id, user=request.user)
    else:
        cart_item = get_object_or_404(CartItem, pk=item_id, session_key=request.session.session_key)

    action = request.POST.get('action')

    if action == 'increment':
        if cart_item.quantity < cart_item.product.stock_quantity:
            cart_item.quantity += 1
            cart_item.save()
        else:
            messages.warning(request, f"Max available stock reached for {cart_item.product.name}.")
    elif action == 'decrement':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
            messages.info(request, "Item removed from cart.")
    elif action == 'set_quantity':
        try:
            new_qty = int(request.POST.get('quantity', 1))
            if new_qty <= 0:
                cart_item.delete()
                messages.info(request, "Item removed from cart.")
            elif new_qty > cart_item.product.stock_quantity:
                cart_item.quantity = cart_item.product.stock_quantity
                cart_item.save()
                messages.warning(request, f"Quantity adjusted to available stock ({cart_item.product.stock_quantity}).")
            else:
                cart_item.quantity = new_qty
                cart_item.save()
        except (ValueError, TypeError):
            pass
    elif action == 'remove':
        cart_item.delete()
        messages.info(request, "Item removed from cart.")

    return redirect('orders:cart_detail')


@login_required
def checkout_view(request):
    cart_items = CartItem.objects.filter(user=request.user).select_related('product')
    if not cart_items.exists():
        messages.warning(request, "Your shopping cart is empty.")
        return redirect('inventory:shop')

    totals = _calculate_cart_totals(cart_items)
    subtotal = totals['subtotal']
    discount = totals['discount']
    shipping_fee = totals['shipping_fee']
    installation_total = totals['installation_total']
    tax = totals['tax']
    total = totals['total']

    profile = getattr(request.user, 'profile', None)
    customer_vehicles = CustomerVehicle.objects.filter(user=request.user)
    service_providers = ServiceProvider.objects.filter(is_active=True)[:6]

    has_installation = any(item.buy_and_install for item in cart_items)

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('shipping_address', '').strip()
        city = request.POST.get('city', '').strip()
        state = request.POST.get('state', '').strip()
        pincode = request.POST.get('pincode', '').strip()
        payment_method = request.POST.get('payment_method', 'cod')
        demo_payment_status = request.POST.get('demo_payment_status', 'success')
        terms_confirmed = request.POST.get('confirm_order') == '1'

        # Server-side validation
        errors = []
        if len(full_name) < 2:
            errors.append("Please enter your full name.")
        if not email or '@' not in email:
            errors.append("Please enter a valid email address.")
        if not phone or len(re.sub(r'\D', '', phone)) < 10:
            errors.append("Please provide a valid 10-digit Indian contact phone number.")
        if not address or len(address) < 5:
            errors.append("Please enter complete street delivery address.")
        if not city:
            errors.append("City is required.")
        if not state:
            errors.append("State is required.")
        if not pincode or not re.match(r'^\d{6}$', pincode.strip()):
            errors.append("Please provide a valid 6-digit Indian postal PIN code.")
        if not terms_confirmed:
            errors.append("Please confirm your order details and demonstration agreement before proceeding.")

        if errors:
            for err in errors:
                messages.error(request, err)
            context = {
                'cart_items': cart_items,
                'subtotal': subtotal,
                'discount': discount,
                'shipping_fee': shipping_fee,
                'installation_total': installation_total,
                'tax': tax,
                'total': total,
                'profile': profile,
                'customer_vehicles': customer_vehicles,
                'service_providers': service_providers,
                'has_installation': has_installation,
            }
            return render(request, 'orders/checkout.html', context)

        # Accidental Duplicate Order Protection
        last_order = Order.objects.filter(user=request.user).order_by('-created_at').first()
        if last_order and last_order.total_amount == total:
            from django.utils import timezone
            import datetime
            if (timezone.now() - last_order.created_at).total_seconds() < 5:
                messages.warning(request, f"Duplicate submission detected. Viewing order {last_order.order_number}.")
                return redirect('orders:order_confirmation', order_number=last_order.order_number)

        # Secure Order Creation inside Database Transaction
        try:
            with transaction.atomic():
                # 1. Lock and validate inventory rows
                for item in cart_items:
                    prod = Product.objects.select_for_update().get(pk=item.product.pk)
                    if prod.stock_quantity < item.quantity:
                        messages.error(request, f"Insufficient stock for {prod.name}. Available: {prod.stock_quantity}.")
                        return redirect('orders:cart_detail')

                # 2. Determine Payment & Order Status
                if payment_method == 'cod':
                    pay_status = 'Pending (Cash on Delivery Demo)'
                    ord_status = 'confirmed'
                elif demo_payment_status == 'fail':
                    pay_status = 'Payment Failed (Demo Simulation)'
                    ord_status = 'pending'
                else:
                    pay_status = 'Paid (Demo Simulated Gateway)'
                    ord_status = 'confirmed'

                # 3. Create Order Record
                order = Order.objects.create(
                    user=request.user,
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    shipping_address=address,
                    city=city,
                    state=state,
                    pincode=pincode,
                    subtotal=subtotal,
                    discount_amount=discount,
                    shipping_fee=shipping_fee,
                    installation_fee=installation_total,
                    tax_amount=tax,
                    total_amount=total,
                    payment_method=payment_method,
                    payment_status=pay_status,
                    is_simulated=True,
                    status=ord_status
                )

                # 4. Create OrderItems & Atomically Deduct Inventory
                for item in cart_items:
                    prod = Product.objects.select_for_update().get(pk=item.product.pk)
                    prev_stock = prod.stock_quantity
                    prod.stock_quantity -= item.quantity
                    prod.save()

                    # Audit Record
                    InventoryRecord.objects.create(
                        product=prod,
                        change_type='sale',
                        quantity=-item.quantity,
                        previous_stock=prev_stock,
                        new_stock=prod.stock_quantity,
                        notes=f"Deducted for Order {order.order_number}"
                    )

                    order_item = OrderItem.objects.create(
                        order=order,
                        product=prod,
                        product_name=prod.name,
                        product_sku=prod.sku,
                        unit_price=prod.final_price,
                        quantity=item.quantity,
                        total_price=prod.final_price * item.quantity,
                        buy_and_install=item.buy_and_install,
                        installation_fee=prod.installation_fee if item.buy_and_install else Decimal('0.00')
                    )

                    # Create Linked Installation Request if Buy + Install
                    if item.buy_and_install and prod.is_installable:
                        InstallationRequest.objects.create(
                            user=request.user,
                            product_name=prod.name,
                            vehicle_info=request.POST.get('install_vehicle', 'Specified Customer Vehicle'),
                            status='pending',
                            estimated_fee=prod.installation_fee,
                            notes=f"Linked to Order {order.order_number} Item #{order_item.id}"
                        )

                # 5. Clear User Cart Items Only After Successful Creation
                cart_items.delete()

                messages.success(request, f"Order {order.order_number} successfully placed (Demonstration Mode).")
                return redirect('orders:order_confirmation', order_number=order.order_number)

        except Exception as e:
            messages.error(request, f"An error occurred while creating your order: {str(e)}")
            return redirect('orders:checkout')

    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'discount': discount,
        'shipping_fee': shipping_fee,
        'installation_total': installation_total,
        'tax': tax,
        'total': total,
        'profile': profile,
        'customer_vehicles': customer_vehicles,
        'service_providers': service_providers,
        'has_installation': has_installation,
    }
    return render(request, 'orders/checkout.html', context)


@login_required
def order_confirmation(request, order_number):
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), order_number=order_number)
    if order.user != request.user and not request.user.is_staff:
        messages.error(request, "You are not authorized to view this order confirmation.")
        return redirect('orders:order_history')

    return render(request, 'orders/order_confirmation.html', {
        'order': order,
        'estimated_days': '3 to 5 business days',
    })


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items')
    return render(request, 'orders/order_history.html', {'orders': orders})


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), order_number=order_number)
    if order.user != request.user and not request.user.is_staff:
        raise Http404("Order not found or access denied.")

    can_cancel = order.status in ['pending', 'confirmed']
    return render(request, 'orders/order_detail.html', {'order': order, 'can_cancel': can_cancel})


@login_required
@require_POST
def cancel_order(request, order_number):
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), order_number=order_number)
    if order.user != request.user and not request.user.is_staff:
        raise Http404("Order not found or access denied.")

    if order.status not in ['pending', 'confirmed']:
        messages.error(request, f"Order {order.order_number} cannot be cancelled as it is already {order.get_status_display()}.")
        return redirect('orders:order_detail', order_number=order.order_number)

    try:
        with transaction.atomic():
            # Restore inventory for all items
            for item in order.items.all():
                prod = Product.objects.select_for_update().get(pk=item.product.pk)
                prev_stock = prod.stock_quantity
                prod.stock_quantity += item.quantity
                prod.save()

                InventoryRecord.objects.create(
                    product=prod,
                    change_type='cancellation_restock',
                    quantity=item.quantity,
                    previous_stock=prev_stock,
                    new_stock=prod.stock_quantity,
                    notes=f"Stock restored due to cancellation of Order {order.order_number}"
                )

            order.status = 'cancelled'
            if 'Paid' in order.payment_status:
                order.payment_status = 'Refund Processed (Demo Simulated)'
            order.save()

            messages.success(request, f"Order {order.order_number} has been cancelled and stock has been restored.")
    except Exception as e:
        messages.error(request, f"Failed to cancel order: {str(e)}")

    return redirect('orders:order_detail', order_number=order.order_number)
