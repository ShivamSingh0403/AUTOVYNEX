from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_POST
from decimal import Decimal
from .models import CartItem, Order, OrderItem
from inventory.models import Product, InventoryRecord
from services.models import InstallationRequest, ServiceProvider
from garage.models import CustomerVehicle


def _get_cart_queryset(request):
    if request.user.is_authenticated:
        return CartItem.objects.filter(user=request.user).select_related('product')
    else:
        if not request.session.session_key:
            request.session.create()
        return CartItem.objects.filter(session_key=request.session.session_key).select_related('product')


def cart_detail(request):
    cart_items = _get_cart_queryset(request)
    
    subtotal = sum(item.item_subtotal for item in cart_items)
    # Apply demo festive discount if subtotal > 4000
    discount = Decimal('500.00') if subtotal >= 4000 else Decimal('0.00')
    shipping_fee = Decimal('0.00') if subtotal >= 999 or subtotal == 0 else Decimal('150.00')
    tax = (subtotal - discount) * Decimal('0.18') if subtotal > discount else Decimal('0.00')
    total = (subtotal - discount) + shipping_fee + tax

    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'discount': discount,
        'shipping_fee': shipping_fee,
        'tax': tax,
        'total': total,
    }
    return render(request, 'orders/cart.html', context)


@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    quantity = int(request.POST.get('quantity', 1))
    buy_and_install = request.POST.get('buy_and_install') == '1'

    if not product.in_stock:
        messages.error(request, f"Sorry, {product.name} is currently out of stock.")
        return redirect(request.META.get('HTTP_REFERER', 'inventory:shop'))

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
        if buy_and_install:
            cart_item.buy_and_install = True
        cart_item.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('accept') == 'application/json':
        cart_items = _get_cart_queryset(request)
        new_cart_count = sum(item.quantity for item in cart_items)
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
def update_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, pk=item_id)
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

    subtotal = sum(item.item_subtotal for item in cart_items)
    discount = Decimal('500.00') if subtotal >= 4000 else Decimal('0.00')
    shipping_fee = Decimal('0.00') if subtotal >= 999 else Decimal('150.00')
    tax = (subtotal - discount) * Decimal('0.18') if subtotal > discount else Decimal('0.00')
    total = (subtotal - discount) + shipping_fee + tax

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
        payment_method = request.POST.get('payment_method', 'simulated_upi')

        if not (full_name and email and phone and address and city and state and pincode):
            messages.error(request, "Please fill in all mandatory shipping address fields.")
            return redirect('orders:checkout')

        # Stock Validation inside Database Transaction
        try:
            with transaction.atomic():
                for item in cart_items:
                    # Lock product record
                    prod = Product.objects.select_for_update().get(pk=item.product.pk)
                    if prod.stock_quantity < item.quantity:
                        messages.error(request, f"Insufficient stock for {prod.name}. Available: {prod.stock_quantity}.")
                        return redirect('orders:cart_detail')

                # Create Order
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
                    tax_amount=tax,
                    total_amount=total,
                    payment_method=payment_method,
                    payment_status='Simulated Payment Success',
                    is_simulated=True,
                    status='confirmed'
                )

                # Create OrderItems and Deduct Inventory
                for item in cart_items:
                    prod = Product.objects.select_for_update().get(pk=item.product.pk)
                    prev_stock = prod.stock_quantity
                    prod.stock_quantity -= item.quantity
                    prod.save()

                    # Audit Log
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

                    # Create InstallationRequest record if Buy + Install was selected
                    if item.buy_and_install:
                        InstallationRequest.objects.create(
                            user=request.user,
                            product_name=prod.name,
                            vehicle_info=request.POST.get('install_vehicle', 'User Vehicle Specified on Booking'),
                            status='pending',
                            estimated_fee=prod.installation_fee,
                            notes=f"Linked to Order {order.order_number} Item #{order_item.id}"
                        )

                # Clear User Cart
                cart_items.delete()

                messages.success(request, f"Congratulations! Your order {order.order_number} has been confirmed (Demonstration Simulation).")
                return redirect('orders:order_detail', order_number=order.order_number)

        except Exception as e:
            messages.error(request, f"An error occurred while creating your order: {str(e)}")
            return redirect('orders:checkout')

    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'discount': discount,
        'shipping_fee': shipping_fee,
        'tax': tax,
        'total': total,
        'profile': profile,
        'customer_vehicles': customer_vehicles,
        'service_providers': service_providers,
        'has_installation': has_installation,
    }
    return render(request, 'orders/checkout.html', context)


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items')
    return render(request, 'orders/order_history.html', {'orders': orders})


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), order_number=order_number)
    # Ensure privacy: users can only view their own orders unless staff
    if order.user != request.user and not request.user.is_staff:
        messages.error(request, "You are not authorized to view this order.")
        return redirect('orders:order_history')

    return render(request, 'orders/order_detail.html', {'order': order})
