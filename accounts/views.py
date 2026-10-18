from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import CustomerProfile, Notification


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:customer_dashboard')

    if request.method == 'POST':
        username_or_email = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # Allow login by username or email
        user = authenticate(request, username=username_or_email, password=password)
        if not user:
            try:
                user_obj = User.objects.get(email=username_or_email)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None

        if user is not None:
            old_session_key = request.session.session_key
            login(request, user)

            # 1. Merge guest cart into user cart
            if old_session_key:
                from orders.models import CartItem
                guest_items = CartItem.objects.filter(session_key=old_session_key).select_related('product')
                for g_item in guest_items:
                    user_item = CartItem.objects.filter(user=user, product=g_item.product).first()
                    if user_item:
                        user_item.quantity = min(user_item.quantity + g_item.quantity, g_item.product.stock_quantity)
                        if g_item.buy_and_install:
                            user_item.buy_and_install = True
                        user_item.save()
                        g_item.delete()
                    else:
                        g_item.user = user
                        g_item.session_key = ''
                        g_item.save()

            # 2. Sync / Restore selected vehicle
            if not request.session.get('selected_variant_id'):
                if hasattr(user, 'profile') and user.profile.selected_vehicle:
                    request.session['selected_variant_id'] = user.profile.selected_vehicle.id
                elif hasattr(user, 'garage_vehicles') and user.garage_vehicles.exists():
                    default_gv = user.garage_vehicles.filter(is_default=True).first() or user.garage_vehicles.first()
                    if default_gv:
                        request.session['selected_variant_id'] = default_gv.variant.id
            elif hasattr(user, 'profile') and not user.profile.selected_vehicle:
                user.profile.selected_vehicle_id = request.session.get('selected_variant_id')
                user.profile.save(update_fields=['selected_vehicle'])

            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('dashboard:customer_dashboard')
        else:
            messages.error(request, "Invalid username/email or password.")

    return render(request, 'accounts/login.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:customer_dashboard')

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        phone = request.POST.get('phone', '').strip()
        city = request.POST.get('city', 'Bengaluru').strip()

        if not (full_name and email and password):
            messages.error(request, "Please fill in all mandatory fields.")
            return redirect('accounts:register')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('accounts:register')

        if User.objects.filter(email=email).exists():
            messages.error(request, "An account with this email address already exists.")
            return redirect('accounts:register')

        # Username generation
        username = email.split('@')[0]
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        profile, _ = CustomerProfile.objects.get_or_create(user=user)
        profile.phone = phone
        profile.city = city
        profile.save()

        # Welcome notification
        Notification.objects.create(
            user=user,
            title='Welcome to AUTOVYNEX!',
            message='Your automotive profile is ready. Add your vehicle to My Garage for guaranteed compatible spare parts.',
            link='/garage/',
            notification_type='promo'
        )

        login(request, user)
        messages.success(request, f"Welcome to AUTOVYNEX, {first_name}! Your account has been registered.")
        return redirect('dashboard:customer_dashboard')

    return render(request, 'accounts/register.html')


def forgot_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        messages.success(request, f"If an account with {email} exists, a secure password reset link has been dispatched (Simulated Demo).")
        return redirect('accounts:login')

    return render(request, 'accounts/forgot_password.html')


def logout_view(request):
    logout(request)
    messages.info(request, "You have been securely signed out.")
    return redirect('core:home')


@login_required
def profile_settings(request):
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        state = request.POST.get('state', '').strip()
        pincode = request.POST.get('pincode', '').strip()

        request.user.first_name = first_name
        request.user.last_name = last_name
        request.user.save()

        profile.phone = phone
        profile.address = address
        profile.city = city
        profile.state = state
        profile.pincode = pincode
        profile.save()

        messages.success(request, "Your profile coordinates have been updated!")
        return redirect('accounts:profile_settings')

    return render(request, 'accounts/profile.html', {'profile': profile})


@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(user=request.user)
    
    # Mark all as read when viewed
    if request.GET.get('mark_read') == '1':
        notifications.update(is_read=True)
        messages.info(request, "All notifications marked as read.")
        return redirect('accounts:notifications')

    return render(request, 'accounts/notifications.html', {'notifications': notifications})
