from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from inventory.models import Product, ProductCategory, Brand
from vehicles.models import VehicleMake, VehicleModel
from services.models import Service, ServiceProvider
from used_cars.models import UsedCarListing
from core.models import NewsletterSubscriber, ContactMessage


def home(request):
    featured_products = Product.objects.filter(is_active=True, is_featured=True).select_related('category', 'brand')[:12]
    if not featured_products or featured_products.count() < 8:
        featured_products = Product.objects.filter(is_active=True).select_related('category', 'brand')[:16]

    popular_categories = ProductCategory.objects.all().order_by('sort_order')[:12]
    featured_services = Service.objects.all()[:6]
    used_cars = UsedCarListing.objects.filter(is_approved=True, is_sold=False)[:3]
    top_brands = Brand.objects.all()[:8]
    all_makes = VehicleMake.objects.all().order_by('name')

    # Compatible products if user has active vehicle
    compatible_products = []
    selected_variant_id = request.session.get('selected_variant_id')
    if selected_variant_id:
        compatible_products = Product.objects.filter(
            fitments__variant_id=selected_variant_id,
            is_active=True
        ).select_related('category', 'brand')[:6]

    # User wishlist IDs
    user_wishlist_ids = set()
    if request.user.is_authenticated:
        from inventory.models import WishlistItem
        user_wishlist_ids = set(WishlistItem.objects.filter(user=request.user).values_list('product_id', flat=True))

    context = {
        'featured_products': featured_products,
        'popular_categories': popular_categories,
        'featured_services': featured_services,
        'used_cars': used_cars,
        'top_brands': top_brands,
        'all_makes': all_makes,
        'compatible_products': compatible_products,
        'user_wishlist_ids': user_wishlist_ids,
    }
    return render(request, 'core/home.html', context)


def about(request):
    return render(request, 'core/about.html')


def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        subject = request.POST.get('subject', '').strip()
        message_text = request.POST.get('message', '').strip()

        if name and email and subject and message_text:
            ContactMessage.objects.create(
                name=name, email=email, phone=phone,
                subject=subject, message=message_text
            )
            messages.success(request, "Your message has been received! An AUTOVYNEX automotive engineer will contact you shortly.")
            return redirect('core:contact')
        else:
            messages.error(request, "Please fill in all required fields.")

    return render(request, 'core/contact.html')


def offers(request):
    discounted_products = Product.objects.filter(is_active=True, discount_price__isnull=False).select_related('category', 'brand')[:16]
    return render(request, 'core/offers.html', {'discounted_products': discounted_products})


def car_valuation(request):
    valuation_record = None
    if request.method == 'POST':
        make_name = request.POST.get('make_name', 'Maruti Suzuki').strip()
        model_name = request.POST.get('model_name', 'Swift').strip()
        year = int(request.POST.get('year', 2022))
        mileage = int(request.POST.get('mileage', 35000))
        fuel_type = request.POST.get('fuel_type', 'Petrol').strip()
        transmission = request.POST.get('transmission', 'Manual').strip()
        condition = request.POST.get('condition', 'good').strip()
        orig_price = float(request.POST.get('original_price', 1000000))

        # Algorithmic depreciation estimation
        age = max(0, 2026 - year)
        depreciation_rate = min(0.70, 0.15 + (age * 0.08) + (mileage / 100000 * 0.10))
        if condition == 'excellent':
            depreciation_rate -= 0.05
        elif condition == 'fair':
            depreciation_rate += 0.08

        base_val = orig_price * (1 - depreciation_rate)
        min_val = round(base_val * 0.94, -2)
        max_val = round(base_val * 1.06, -2)

        from used_cars.models import CarValuationRecord
        valuation_record = CarValuationRecord.objects.create(
            user=request.user if request.user.is_authenticated else None,
            make_name=make_name,
            model_name=model_name,
            year=year,
            mileage=mileage,
            fuel_type=fuel_type,
            transmission=transmission,
            condition=condition,
            estimated_price_min=min_val,
            estimated_price_max=max_val,
            is_estimate_only=True
        )

        from django.http import JsonResponse
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'min_price': float(min_val),
                'max_price': float(max_val),
                'disclaimer': 'Estimated fair market value range. Not a guaranteed purchase offer.'
            })

    return render(request, 'core/car_valuation.html', {'valuation_record': valuation_record})


def fuel_calculator(request):
    return render(request, 'core/fuel_calculator.html')


def ownership_calculator(request):
    return render(request, 'core/ownership_calculator.html')


def ai_car_help(request):
    return render(request, 'core/ai_car_help.html')


def privacy_policy(request):
    return render(request, 'core/privacy_policy.html')


def terms_conditions(request):
    return render(request, 'core/terms_conditions.html')


@require_POST
def newsletter_subscribe(request):
    email = request.POST.get('email', '').strip()
    if email:
        NewsletterSubscriber.objects.get_or_create(email=email)
        messages.success(request, f"Thank you! {email} has been subscribed to AUTOVYNEX car care insights and discounts.")
    return redirect(request.META.get('HTTP_REFERER', 'core:home'))


def custom_404_view(request, exception=None):
    return render(request, '404.html', status=404)
